import sqlite3
from datetime import datetime
from typing import Optional, Dict, Tuple, List, Any, Iterator

from tabun_stat import types
from tabun_stat.datasource.base import BaseDataSource, DataNotFound


class Sqlite3DataSource(BaseDataSource):
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: Optional[sqlite3.Connection] = None

        # Кэш статусов блогов по их id
        self._blog_status_by_id: Dict[int, int] = {}
        # Кэш статусов блогов по их slug
        self._blog_status_by_slug: Dict[str, int] = {}
        # Кэш айдишников блогов по slug
        self._blog_ids: Dict[str, int] = {}
        # Кэш блогов постов
        self._post_blogs: Dict[int, Optional[int]] = {}
        # Кэш имён пользователей по их id
        self._usernames: Dict[int, str] = {}
        self.reconnect()

    def close(self) -> None:
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
        self.close()

        try:
            self._conn = sqlite3.connect(self._path)
        except Exception:
            self._conn = None
            raise

        # Сразу предзагружаем кэши
        self._fetch_blog_info()

    def _fetch_blog_info(self) -> None:
        blogs_status = self.fetchall_dict('select id, slug, status from blogs')
        self._blog_status_by_id = {
            x['id']: x['status']
            for x in blogs_status
        }
        self._blog_status_by_slug = {
            x['slug']: x['status']
            for x in blogs_status
        }
        self._blog_ids = {x['slug']: x['id'] for x in blogs_status}

    def execute(self, sql: str, args: Tuple[Any, ...] = ()) -> Any:
        cur = self._conn.cursor()  # type: ignore
        cur.execute(sql, args)
        return cur

    def fetchall(self, sql: str, args: Tuple[Any, ...] = ()) -> List[Tuple[Any, ...]]:
        return self.execute(sql, args).fetchall()  # type: ignore

    def fetchall_dict(self, sql: str, args: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        c = self.execute(sql, args)
        colnames = [x[0] for x in c.description]
        result_tuple = c.fetchall()
        return [dict(zip(colnames, x)) for x in result_tuple]

    # Табунчане

    def get_user_by_id(self, user_id: int) -> types.User:
        item = self.fetchall_dict('select * from users where id = ?', (user_id,))
        if not item:
            raise DataNotFound
        return self._dict2user(item[0])

    def get_user_by_name(self, username: str) -> types.User:
        item = self.fetchall_dict('select * from users where username = ?', (username,))
        if not item:
            raise DataNotFound
        return self._dict2user(item[0])

    def iter_users(self, filters: Optional[Dict[str, Any]] = None) -> Iterator[List[types.User]]:
        stat = self.get_users_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        where, where_args = build_filter('user', filters, prefix=' AND ')

        last_id = stat.first_id - 1
        while last_id < stat.last_id:
            users = self.fetchall_dict(
                'select * from users where id >= ?{} order by id limit 1000'.format(where),
                (last_id + 1,) + where_args,
            )
            if not users:
                break

            result = [self._dict2user(x) for x in users]
            last_id = result[-1].id
            yield result

    def get_users_limits(self, filters: Optional[Dict[str, Any]] = None) -> types.UsersLimits:
        where, where_args = build_filter('user', filters, prefix=' where ')

        return types.UsersLimits(**self.fetchall_dict(
            'select min(id) first_id, max(id) last_id, count(id) `count` '
            'from users' + where, where_args
        )[0])

    def get_username_by_user_id(self, user_id: int) -> str:
        if user_id not in self._usernames:
            return self.get_user_by_id(user_id).username
        return self._usernames[user_id]

    def _dict2user(self, raw_item: Dict[str, Any]) -> types.User:
        # Попутно заполняем кэш юзернеймов
        self._usernames[raw_item['id']] = raw_item['username']

        item = raw_item.copy()
        item['registered_at'] = datetime.strptime(item['registered_at'], '%Y-%m-%d %H:%M:%S')
        if item['birthday']:
            item['birthday'] = datetime.strptime(item['birthday'], '%Y-%m-%d').date()
        return types.User(**item)

    # Блоги

    def get_blog_by_id(self, blog_id: int) -> types.Blog:
        item = self.fetchall_dict('select * from blogs where id = ?', (blog_id,))
        if not item:
            raise DataNotFound
        return self._dict2blog(item[0])

    def get_blog_by_slug(self, slug: str) -> types.Blog:
        item = self.fetchall_dict('select * from blogs where slug = ?', (slug,))
        if not item:
            raise DataNotFound
        return self._dict2blog(item[0])

    def get_blog_status_by_id(self, blog_id: Optional[int]) -> int:
        if blog_id is None:
            return 0
        if not self._blog_status_by_id:
            self._fetch_blog_info()
        try:
            return self._blog_status_by_id[blog_id]
        except KeyError:
            raise DataNotFound

    def get_blog_status_by_slug(self, slug: Optional[str]) -> int:
        if not slug:
            return 0
        if not self._blog_status_by_slug:
            self._fetch_blog_info()
        try:
            return self._blog_status_by_slug[slug]
        except KeyError:
            raise DataNotFound

    def get_blog_id_by_slug(self, slug: str) -> int:
        if not self._blog_status_by_slug:
            self._fetch_blog_info()
        try:
            return self._blog_ids[slug]
        except KeyError:
            raise DataNotFound

    def get_blog_id_of_post(self, post_id: int) -> Optional[int]:
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

    def iter_blogs(self, filters: Optional[Dict[str, Any]] = None) -> Iterator[List[types.Blog]]:
        stat = self.get_blogs_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        where, where_args = build_filter('blog', filters, prefix=' AND ')

        last_id = stat.first_id - 1
        while last_id < stat.last_id:
            blogs = self.fetchall_dict(
                'select * from blogs where id >= ?{} order by id limit 1000'.format(where),
                (last_id + 1,) + where_args,
            )
            if not blogs:
                break

            result = [self._dict2blog(x) for x in blogs]
            last_id = result[-1].id
            yield result

    def get_blogs_limits(self, filters: Optional[Dict[str, Any]] = None) -> types.BlogsLimits:
        where, where_args = build_filter('blog', filters, prefix=' where ')

        return types.BlogsLimits(**self.fetchall_dict(
            'select min(id) first_id, max(id) last_id, count(id) `count` '
            'from blogs' + where, where_args
        )[0])

    def _dict2blog(self, raw_item: Dict[str, Any]) -> types.Blog:
        item = raw_item.copy()
        item['created_at'] = datetime.strptime(item['created_at'], '%Y-%m-%d %H:%M:%S')
        item['deleted'] = bool(item['deleted'])
        return types.Blog(**item)

    # Посты (опционально с комментами)

    def get_post_by_id(self, post_id: int, with_comments: bool = False) -> types.Post:
        item = self.fetchall_dict('select * from posts where id = ?', (post_id,))
        if not item:
            raise DataNotFound
        post = self._dict2post(item[0])
        if with_comments:
            post.comments = self.get_post_comments(post_id)
        return post

    def iter_posts(self, with_comments: bool = False, filters: Optional[Dict[str, Any]] = None) -> Iterator[List[types.Post]]:
        stat = self.get_posts_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        where, where_args = build_filter('post', filters, prefix=' AND ')

        last_id = stat.first_id - 1
        while last_id < stat.last_id:
            posts = self.fetchall_dict(
                'select * from posts where id >= ?{} order by id limit 1000'.format(where),
                (last_id + 1,) + where_args,
            )
            if not posts:
                break

            comments_dict: Optional[Dict[int, List[types.Comment]]] = None
            if with_comments:
                comments_dict = {x['id']: [] for x in posts}
                comments_list = self.fetchall_dict(
                    'select * from comments where post_id >= ? and post_id <= ?',
                    (posts[0]['id'], posts[-1]['id'])
                )
                for c in comments_list:
                    comments_dict[c['id']].append(self._dict2comment(c))
                del comments_list

            posts_ready: List[types.Post] = []
            for x in posts:
                post = self._dict2post(x)
                if comments_dict is not None:
                    post.comments = comments_dict.pop(post.id)
                    post.comments.sort(key=lambda c: c.id)
                posts_ready.append(post)

            assert posts_ready
            last_id = posts_ready[-1].id
            yield posts_ready

    def get_posts_limits(self, filters: Optional[Dict[str, Any]] = None) -> types.PostsLimits:
        where, where_args = build_filter('post', filters, prefix=' where ')

        result = self.fetchall_dict(
            'select min(id) first_id, max(id) last_id, count(id) `count`, '
            'min(created_at) first_created_at, max(created_at) last_created_at '
            'from posts' + where, where_args
        )[0]
        if result['first_created_at'] is not None:
            result['first_created_at'] = datetime.strptime(result['first_created_at'], '%Y-%m-%d %H:%M:%S')
        if result['last_created_at'] is not None:
            result['last_created_at'] = datetime.strptime(result['last_created_at'], '%Y-%m-%d %H:%M:%S')
        return types.PostsLimits(**result)

    def _dict2post(self, raw_item: Dict[str, Any]) -> types.Post:
        # Попутно заполняем кэш блогов
        self._post_blogs[raw_item['id']] = raw_item['blog_id'] or None

        item = raw_item.copy()
        item['created_at'] = datetime.strptime(item['created_at'], '%Y-%m-%d %H:%M:%S')
        item['deleted'] = bool(item['deleted'])
        item['draft'] = bool(item['draft'])
        return types.Post(**item)

    # Комменты

    def get_comment_by_id(self, comment_id: int) -> types.Comment:
        item = self.fetchall_dict('select * from comments where id = ?', (comment_id,))
        if not item:
            raise DataNotFound
        comment = self._dict2comment(item[0])
        return comment

    def get_post_comments(self, post_id: int) -> List[types.Comment]:
        items = self.fetchall_dict(
            'select * from comments where post_id = ?',
            (post_id,)
        )

        result = [self._dict2comment(x) for x in items]
        result.sort(key=lambda c: c.id)
        return result

    def iter_comments(self, filters: Optional[Dict[str, Any]] = None) -> Iterator[List[types.Comment]]:
        stat = self.get_comments_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        where, where_args = build_filter('comment', filters, prefix=' AND ')

        last_id = stat.first_id - 1
        while True:
            comments = self.fetchall_dict(
                'select * from comments where id >= ?{} order by id limit 10000'.format(where),
                (last_id + 1,) + where_args,
            )
            if not comments:
                break

            result = [self._dict2comment(x) for x in comments]
            yield result
            last_id = result[-1].id

    def get_comments_limits(self, filters: Optional[Dict[str, Any]] = None) -> types.CommentsLimits:
        where, where_args = build_filter('comment', filters, prefix=' where ')

        result = self.fetchall_dict(
            'select min(id) first_id, max(id) last_id, count(id) `count`, '
            'min(created_at) first_created_at, max(created_at) last_created_at '
            'from comments' + where, where_args
        )[0]
        if result['first_created_at'] is not None:
            result['first_created_at'] = datetime.strptime(result['first_created_at'], '%Y-%m-%d %H:%M:%S')
        if result['last_created_at'] is not None:
            result['last_created_at'] = datetime.strptime(result['last_created_at'], '%Y-%m-%d %H:%M:%S')
        return types.CommentsLimits(**result)

    def _dict2comment(self, raw_item: Dict[str, Any]) -> types.Comment:
        item = raw_item.copy()
        item['created_at'] = datetime.strptime(item['created_at'], '%Y-%m-%d %H:%M:%S')
        item['deleted'] = bool(item['deleted'])
        return types.Comment(**item)


def build_filter(type: str, filters: Optional[Dict[str, Any]] = None, prefix: str = '') -> Tuple[str, Tuple[Any, ...]]:
    # pylint: disable=W0622

    if not filters:
        return '', ()

    where = []
    where_args = []

    for k, v in filters.items():
        if '__' in k:
            key, act = k.rsplit('__', 1)
        else:
            key, act = k, '?'

        if key.startswith(type + '_'):
            # Используем правильное имя для первичного ключа таблицы (post_id -> id)
            key = key[len(type) + 1:]

        if act == 'lt':
            where.append('`{}` < ?'.format(key))
            where_args.append(v)
        elif act == 'lte':
            where.append('`{}` <= ?'.format(key))
            where_args.append(v)
        elif act == 'gt':
            where.append('`{}` > ?'.format(key))
            where_args.append(v)
        elif act == 'gte':
            where.append('`{}` >= ?'.format(key))
            where_args.append(v)
        else:
            raise ValueError('Invalid {} filter: {!r}'.format(type, k))

    return prefix + ' AND '.join(where), tuple(where_args)
