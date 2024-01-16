import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Cursor
from threading import Lock
from typing import Any, Collection, Iterator

from tabun_stat import types
from tabun_stat.datasource.base import BaseDataSource, DataNotFound
from tabun_stat.stat import TabunStat
from tabun_stat.utils import filter_split


class Sqlite3DataSource(BaseDataSource):
    def __init__(self, *, path: str | Path):
        super().__init__()

        self._path = path
        self._conn: sqlite3.Connection | None = None
        self._lock = Lock()

        # Кэш статусов блогов по их id
        self._blog_status_by_id: dict[int, int] = {}
        # Кэш блогов постов
        self._post_blogs: dict[int, int | None] = {}
        # Кэш имён пользователей по их id
        self._usernames: dict[int, str] = {}

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def destroy(self) -> None:
        # При уничтожении отключаемся от БД
        self.close()

    def __del__(self) -> None:
        self.close()

    def reconnect(self) -> None:
        # Если нас просят переподключиться, но БД уже подключена,
        # то отключаем её
        with self._lock:
            if self._conn is not None:
                self._conn.close()

            try:
                self._conn = sqlite3.connect(self._path, check_same_thread=False)
            except Exception:
                self._conn = None
                raise

        # Сразу предзагружаем кэши
        self._fetch_blog_info()

    def start(self, stat: TabunStat) -> None:
        if self._conn is None:
            self.reconnect()

    def _fetch_blog_info(self) -> None:
        blogs_status = self.fetchall("select id, status from blogs")
        with self._lock:
            self._blog_status_by_id = dict(blogs_status)

    def _execute(self, sql: str, args: tuple[Any, ...] = ()) -> Cursor:
        if self._conn is None:
            raise RuntimeError("Not connected")
        cur = self._conn.cursor()
        cur.execute(sql, args)
        return cur

    def fetchall(self, sql: str, args: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self._lock:
            cur = self._execute(sql, args)
            result = cur.fetchall()
            cur.close()
        return result

    def fetchall_dict(self, sql: str, args: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._execute(sql, args)
            colnames = [x[0] for x in cur.description]
            result_tuple = cur.fetchall()
            cur.close()
        return [dict(zip(colnames, x)) for x in result_tuple]

    # Табунчане

    def get_user_by_id(self, user_id: int) -> types.User:
        item = self.fetchall_dict("select * from users where id = ?", (user_id,))
        if not item:
            raise DataNotFound
        return self._dict2user(item[0])

    def iter_users(self, filters: dict[str, Any] | None = None) -> Iterator[list[types.User]]:
        stat = self.get_users_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        where, where_args = build_filter("user", filters, prefix=" AND ")

        last_id = stat.first_id - 1
        while last_id < stat.last_id:
            users = self.fetchall_dict(
                f"select * from users where id >= ?{where} order by id limit 1000",
                (last_id + 1,) + where_args,
            )
            if not users:
                break

            result = [self._dict2user(x) for x in users]
            last_id = result[-1].id
            yield result

    def get_users_limits(self, filters: dict[str, Any] | None = None) -> types.UsersLimits:
        where, where_args = build_filter("user", filters, prefix=" where ")

        return types.UsersLimits(
            **self.fetchall_dict(
                "select min(id) first_id, max(id) last_id, count(id) `count` " "from users" + where,
                where_args,
            )[0]
        )

    def get_username_by_user_id(self, user_id: int) -> str:
        if user_id not in self._usernames:
            return self.get_user_by_id(user_id).username
        return self._usernames[user_id]

    def _dict2user(self, raw_item: dict[str, Any]) -> types.User:
        # Попутно заполняем кэш юзернеймов
        self._usernames[raw_item["id"]] = raw_item["username"]

        item = raw_item.copy()
        item["registered_at"] = _parse_utc_datetime(item["registered_at"])
        if item["birthday"]:
            item["birthday"] = datetime.strptime(item["birthday"], "%Y-%m-%d").date()
        return types.User(**item)

    # Блоги

    def get_blog_by_id(self, blog_id: int) -> types.Blog:
        item = self.fetchall_dict("select * from blogs where id = ?", (blog_id,))
        if not item:
            raise DataNotFound
        return self._dict2blog(item[0])

    def get_blog_status_by_id(self, blog_id: int | None) -> int:
        if blog_id is None:
            return 0
        if not self._blog_status_by_id:
            self._fetch_blog_info()
        try:
            return self._blog_status_by_id[blog_id]
        except KeyError as exc:
            raise DataNotFound from exc

    def get_blog_statuses_by_ids(self, blog_ids: Collection[int]) -> dict[int, int]:
        if not self._blog_status_by_id:
            self._fetch_blog_info()

        result = {}
        for blog_id in blog_ids:
            try:
                result[blog_id] = self._blog_status_by_id[blog_id]
            except KeyError:
                pass
        return result

    def get_blog_id_of_post(self, post_id: int) -> int | None:
        if post_id not in self._post_blogs:
            try:
                self._post_blogs[post_id] = self.get_post_by_id(post_id).blog_id
            except DataNotFound:
                self._post_blogs[post_id] = -1  # кэшируем ошибку таким образом
                raise

        blog_id = self._post_blogs[post_id]
        if blog_id == -1:
            raise DataNotFound
        return blog_id

    def get_blog_ids_of_posts(self, post_ids: Collection[int]) -> dict[int, int | None]:
        missing_post_ids = []
        result = {}

        # Сперва проверяем наличие блогов в кэше
        for post_id in post_ids:
            try:
                blog_id = self._post_blogs[post_id]
            except KeyError:
                missing_post_ids.append(post_id)
            else:
                if blog_id != -1:  # -1 означает, что пост не существует
                    result[post_id] = blog_id

        # Чего не оказалось в кэше, то запрашиваем из базы
        if missing_post_ids:
            missing_post_ids_str = ", ".join(str(int(post_id)) for post_id in missing_post_ids)
            blog_ids = dict(
                self.fetchall(
                    f"select id, blog_id from posts where id in ({missing_post_ids_str})",
                )
            )
            for post_id in missing_post_ids:
                try:
                    blog_id = blog_ids[post_id]
                except KeyError:
                    self._post_blogs[post_id] = -1
                else:
                    self._post_blogs[post_id] = blog_id
                    result[post_id] = blog_id

        return result

    def iter_blogs(self, filters: dict[str, Any] | None = None) -> Iterator[list[types.Blog]]:
        stat = self.get_blogs_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        where, where_args = build_filter("blog", filters, prefix=" AND ")

        last_id = stat.first_id - 1
        while last_id < stat.last_id:
            blogs = self.fetchall_dict(
                f"select * from blogs where id >= ?{where} order by id limit 1000",
                (last_id + 1,) + where_args,
            )
            if not blogs:
                break

            result = [self._dict2blog(x) for x in blogs]
            last_id = result[-1].id
            yield result

    def get_blogs_limits(self, filters: dict[str, Any] | None = None) -> types.BlogsLimits:
        where, where_args = build_filter("blog", filters, prefix=" where ")

        return types.BlogsLimits(
            **self.fetchall_dict(
                f"select min(id) first_id, max(id) last_id, count(id) `count` from blogs{where}",
                where_args,
            )[0]
        )

    def _dict2blog(self, raw_item: dict[str, Any]) -> types.Blog:
        item = raw_item.copy()
        item["created_at"] = _parse_utc_datetime(item["created_at"])
        return types.Blog(**item)

    # Посты (опционально с комментами)

    def get_post_by_id(self, post_id: int) -> types.Post:
        item = self.fetchall_dict("select * from posts where id = ?", (post_id,))
        if not item:
            raise DataNotFound
        post = self._dict2post(item[0])
        return post

    def iter_posts(
        self,
        *,
        filters: dict[str, Any] | None = None,
        burst: bool = False,
    ) -> Iterator[list[types.Post]]:
        stat = self.get_posts_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        where, where_args = build_filter("post", filters, prefix=" AND ")

        last_id = stat.first_id - 1
        while last_id < stat.last_id:
            posts = self.fetchall_dict(
                f"select * from posts where id >= ?{where}" + ("" if burst else " order by id limit 1000"),
                (last_id + 1,) + where_args,
            )
            if not posts:
                break

            posts_ready: list[types.Post] = [self._dict2post(x) for x in posts]
            last_id = posts_ready[-1].id
            yield posts_ready

            if burst:
                break

    def get_posts_limits(self, filters: dict[str, Any] | None = None) -> types.PostsLimits:
        where, where_args = build_filter("post", filters, prefix=" where ")

        result = self.fetchall_dict(
            "select min(id) first_id, max(id) last_id, count(id) `count`, "
            "min(created_at) first_created_at, max(created_at) last_created_at "
            f"from posts{where}",
            where_args,
        )[0]
        if result["first_created_at"] is not None:
            result["first_created_at"] = _parse_utc_datetime(result["first_created_at"])
        if result["last_created_at"] is not None:
            result["last_created_at"] = _parse_utc_datetime(result["last_created_at"])
        return types.PostsLimits(**result)

    def _dict2post(self, raw_item: dict[str, Any]) -> types.Post:
        # Попутно заполняем кэш блогов
        self._post_blogs[raw_item["id"]] = raw_item["blog_id"] or None

        item = raw_item.copy()
        item["created_at"] = _parse_utc_datetime(item["created_at"])
        item["tags"] = item["tags"].split(",")
        return types.Post(**item)

    # Комменты

    def get_comment_by_id(self, comment_id: int) -> types.Comment:
        item = self.fetchall_dict("select * from comments where id = ?", (comment_id,))
        if not item:
            raise DataNotFound

        try:
            blog_id = self.get_blog_id_of_post(item[0]["post_id"])
        except DataNotFound:
            # Блог неизвестен (то есть пост в базе не существует)
            blog_id = None
            blog_status = None
        else:
            blog_status = self.get_blog_status_by_id(blog_id)

        comment = self._dict2comment(item[0], blog_id=blog_id, blog_status=blog_status)
        return comment

    def iter_comments(
        self,
        *,
        filters: dict[str, Any] | None = None,
        burst: bool = False,
    ) -> Iterator[list[types.Comment]]:
        stat = self.get_comments_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        where, where_args = build_filter("comment", filters, prefix=" AND ")

        last_id = stat.first_id - 1
        while True:
            comments = self.fetchall_dict(
                f"select * from comments where id >= ?{where}"
                + ("" if burst else " order by id limit 10000"),
                (last_id + 1,) + where_args,
            )
            if not comments:
                break

            result = self._dict2comment_multi(comments)
            yield result
            last_id = result[-1].id

            if burst:
                break

    def get_comments_limits(self, filters: dict[str, Any] | None = None) -> types.CommentsLimits:
        where, where_args = build_filter("comment", filters, prefix=" where ")

        result = self.fetchall_dict(
            "select min(id) first_id, max(id) last_id, count(id) `count`, "
            "min(created_at) first_created_at, max(created_at) last_created_at "
            "from comments" + where,
            where_args,
        )[0]
        if result["first_created_at"] is not None:
            result["first_created_at"] = _parse_utc_datetime(result["first_created_at"])
        if result["last_created_at"] is not None:
            result["last_created_at"] = _parse_utc_datetime(result["last_created_at"])
        return types.CommentsLimits(**result)

    def _dict2comment(
        self,
        raw_item: dict[str, Any],
        *,
        blog_id: int | None,
        blog_status: int | None,
    ) -> types.Comment:
        item = raw_item.copy()
        item["created_at"] = _parse_utc_datetime(item["created_at"])
        return types.Comment(**item, blog_id=blog_id, blog_status=blog_status)

    def _dict2comment_multi(self, raw_items: list[dict[str, Any]]) -> list[types.Comment]:
        blog_ids = self.get_blog_ids_of_posts({x["post_id"] for x in raw_items if x["post_id"] is not None})
        blog_statuses = self.get_blog_statuses_by_ids({x for x in blog_ids.values() if x is not None})

        result = []
        for item in raw_items:
            try:
                blog_id = blog_ids[item["post_id"]]
            except KeyError:
                # Блог неизвестен (то есть пост в базе не существует)
                blog_id = None
                blog_status = None
            else:
                blog_status = blog_statuses[blog_id] if blog_id is not None else 0

            result.append(self._dict2comment(item, blog_id=blog_id, blog_status=blog_status))

        return result


def build_filter(
    type: str,
    filters: dict[str, Any] | None = None,
    *,
    prefix: str = "",
) -> tuple[str, tuple[Any, ...]]:
    # pylint: disable=redefined-builtin

    if not filters:
        return "", ()

    where = []
    where_args = []

    for k, v in filters.items():
        if isinstance(v, datetime):
            # В базе данных предполагается хранение UTC
            v = v.astimezone(timezone.utc).replace(tzinfo=None)

        key, act = filter_split(k)

        if key.startswith(type + "_"):
            # Используем правильное имя для первичного ключа таблицы (post_id -> id)
            key = key[len(type) + 1 :]

        if act == "lt":
            where.append(f"`{key}` < ?")
            where_args.append(v)
        elif act == "lte":
            where.append(f"`{key}` <= ?")
            where_args.append(v)
        elif act == "gt":
            where.append(f"`{key}` > ?")
            where_args.append(v)
        elif act == "gte":
            where.append(f"`{key}` >= ?")
            where_args.append(v)
        else:
            raise ValueError(f"Invalid {type} filter: {k!r}")

    return prefix + " AND ".join(where), tuple(where_args)


def _parse_utc_datetime(s: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
