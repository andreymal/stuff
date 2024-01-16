# pylint: disable=unused-argument

import typing
from typing import Any, Collection, Iterator

from tabun_stat import types
from tabun_stat.utils import filter_act, filter_split

if typing.TYPE_CHECKING:
    from tabun_stat.stat import TabunStat


class DataNotFound(Exception):
    pass


class BaseDataSource:
    def start(self, stat: "TabunStat") -> None:
        pass

    def destroy(self) -> None:
        pass

    # Табунчане

    def get_user_by_id(self, user_id: int) -> types.User:
        """Возвращает данные пользователя по его id.
        Если пользователь не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def iter_users(self, filters: dict[str, Any] | None = None) -> Iterator[list[types.User]]:
        """По очереди yield'ит существующих пользователей. Если указаны
        фильтры, то с учётом их ограничений. Сортировка может быть любая.
        Должны быть реализованы следующие фильтры:

        * ``user_id__lt``: id меньше указанного;
        * ``user_id__lte``: id меньше указанного или равен ему;
        * ``user_id__gt``: id больше указанного;
        * ``user_id__gte``: id больше указанного или равен ему.
        * ``registered_at__lt``, ``registered_at__lte``, ``registered_at__gt``,
          ``registered_at__gte``: аналогично для времени регистрации (datetime)
        """

        stat = self.get_users_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        for user_id in range(stat.first_id, stat.last_id + 1):
            try:
                user = self.get_user_by_id(user_id)
            except DataNotFound:
                continue

            if filters is not None:
                for k, v in filters.items():
                    name, act = filter_split(k)
                    if name == "user_id" and not filter_act(act, user.id, v):
                        continue
                    if name == "registered_at" and not filter_act(act, user.registered_at, v):
                        continue

            yield [user]

    def get_username_by_user_id(self, user_id: int) -> str:
        """Возвращает имя пользователя по его id."""
        return self.get_user_by_id(user_id).username

    def get_users_limits(self, filters: dict[str, Any] | None = None) -> types.UsersLimits:
        """Возвращает статистику о существующих пользователях. Если указаны
        фильтры, то с учётом их ограничений.
        """
        raise NotImplementedError

    # Блоги

    def get_blog_by_id(self, blog_id: int) -> types.Blog:
        """Возвращает блог по его id.
        Если блог не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def get_blog_status_by_id(self, blog_id: int | None) -> int:
        """Возвращает статус блога по его id. 0 - открытый блог,
        1 - закрытый, 2 - полузакрытый.

        Если блог не найден, выбрасывает ошибку DataNotFound.
        blog_id = None означает личный блог, и для него всегда должен
        возвращаться ноль (личные блоги всегда открытые).
        """
        if blog_id is None:
            return 0
        return self.get_blog_by_id(blog_id).status

    def get_blog_statuses_by_ids(self, blog_ids: Collection[int]) -> dict[int, int]:
        """Возвращает статусы блогов по их id. 0 - открытый блог,
        1 - закрытый, 2 - полузакрытый. Если блог не существует, то в итоговом
        словаре его вообще не будет.
        """
        result = {}
        for blog_id in blog_ids:
            try:
                result[blog_id] = self.get_blog_status_by_id(blog_id)
            except DataNotFound:
                pass
        return result

    def get_blog_id_of_post(self, post_id: int) -> int | None:
        """Возвращает id блога, в котором находится указанный пост.
        Если в личном блоге, то None.
        """
        return self.get_post_by_id(post_id).blog_id

    def get_blog_ids_of_posts(self, post_ids: Collection[int]) -> dict[int, int | None]:
        """Возвращает id блогов указанных постов. Если в личном блоге, то None.
        Если блог неизвестен (например, по причине отсутствия поста в базе), то
        в итоговом словаре его вообще не будет.
        """
        result = {}
        for post_id in post_ids:
            try:
                result[post_id] = self.get_blog_id_of_post(post_id)
            except DataNotFound:
                pass
        return result

    def iter_blogs(self, filters: dict[str, Any] | None = None) -> Iterator[list[types.Blog]]:
        """По очереди yield'ит существующие блоги. Если указаны фильтры,
        то с учётом их ограничений. Сортировка может быть любая. Должны быть
        реализованы следующие фильтры:

        * ``blog_id__lt``: id меньше указанного;
        * ``blog_id__lte``: id меньше указанного или равен ему;
        * ``blog_id__gt``: id больше указанного;
        * ``blog_id__gte``: id больше указанного или равен ему.
        """
        stat = self.get_blogs_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        for blog_id in range(stat.first_id, stat.last_id + 1):
            try:
                blog = self.get_blog_by_id(blog_id)
            except DataNotFound:
                continue

            if filters is not None:
                for k, v in filters.items():
                    name, act = filter_split(k)
                    if name == "blog_id" and not filter_act(act, blog.id, v):
                        continue

            yield [blog]

    def get_blogs_limits(self, filters: dict[str, Any] | None = None) -> types.BlogsLimits:
        """Возвращает статистику о существующих блогах. Если указаны фильтры,
        то с учётом их ограничений.
        """
        raise NotImplementedError

    # Посты (опционально с комментами)

    def get_post_by_id(self, post_id: int) -> types.Post:
        """Возвращает пост по его id.
        Если пост не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def iter_posts(
        self,
        *,
        filters: dict[str, Any] | None = None,
        burst: bool = False,
    ) -> Iterator[list[types.Post]]:
        """По очереди yield'ит существующие посты. Если указаны фильтры,
        то с учётом их ограничений. Сортировка может быть любая. Должны быть
        реализованы следующие фильтры:

        * ``post_id__lt``: id меньше указанного;
        * ``post_id__lte``: id меньше указанного или равен ему;
        * ``post_id__gt``: id больше указанного;
        * ``post_id__gte``: id больше указанного или равен ему;
        * ``created_at__lt``, ``created_at__lte``, ``created_at__gt``,
          ``created_at__gte``: аналогично для времени создания поста (datetime)

        Параметр burst — подсказка, что вызывающая сторона предполагает, что
        постов в результате должно быть немного и можно выдать их все за раз.
        Это позволяет, например, использовать более оптимальный SQL-запрос.
        """
        stat = self.get_posts_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        for post_id in range(stat.first_id, stat.last_id + 1):
            try:
                post = self.get_post_by_id(post_id)
            except DataNotFound:
                continue

            if filters is not None:
                for k, v in filters.items():
                    name, act = filter_split(k)
                    if name == "post_id" and not filter_act(act, post.id, v):
                        continue
                    if name == "created_at" and not filter_act(act, post.created_at, v):
                        continue

            yield [post]

    def get_posts_limits(self, filters: dict[str, Any] | None = None) -> types.PostsLimits:
        """Возвращает статистику о существующих постах. Если указаны фильтры,
        то с учётом их ограничений.
        """
        raise NotImplementedError

    # Комменты

    def get_comment_by_id(self, comment_id: int) -> types.Comment:
        """Возвращает комментарий по его id.
        Если комментарий не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def iter_comments(
        self,
        *,
        filters: dict[str, Any] | None = None,
        burst: bool = False,
    ) -> Iterator[list[types.Comment]]:
        """По очереди yield'ит существующие комменты. Если указаны фильтры,
        то с учётом их ограничений. Сортировка может быть любая. Должны быть
        реализованы следующие фильтры:

        * ``comment_id__lt``: id меньше указанного;
        * ``comment_id__lte``: id меньше указанного или равен ему;
        * ``comment_id__gt``: id больше указанного;
        * ``comment_id__gte``: id больше указанного или равен ему;
        * ``post_id__lt``, ``post_id__lte``, ``post_id__gt``, ``post_id__gte``:
          аналогично, но для id поста, которому принадлежит коммент;
        * ``created_at__lt``, ``created_at__lte``, ``created_at__gt``,
          ``created_at__gte``: аналогично для времени создания коммента
          (datetime)

        Параметр burst — подсказка, что вызывающая сторона предполагает, что
        комментов в результате должно быть немного и можно выдать их все за раз.
        Это позволяет, например, использовать более оптимальный SQL-запрос.
        """
        stat = self.get_comments_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        for comment_id in range(stat.first_id, stat.last_id + 1):
            try:
                comment = self.get_comment_by_id(comment_id)
            except DataNotFound:
                continue

            if filters is not None:
                for k, v in filters.items():
                    name, act = filter_split(k)
                    if name == "comment_id" and not filter_act(act, comment.id, v):
                        continue
                    if name == "post_id" and not filter_act(act, comment.post_id, v):
                        continue
                    if name == "created_at" and not filter_act(act, comment.created_at, v):
                        continue

            yield [comment]

    def get_comments_limits(self, filters: dict[str, Any] | None = None) -> types.CommentsLimits:
        """Возвращает статистику о всех существующих комментах. Если указаны
        фильтры, то с учётом их ограничений.
        """
        raise NotImplementedError
