from typing import Optional, Iterator, List, Dict, Any

from tabun_stat import types


__all__ = ['DataNotFound', 'BaseDataSource']


class DataNotFound(Exception):
    pass


class BaseDataSource:
    def destroy(self) -> None:
        pass

    # Табунчане

    def get_user_by_id(self, user_id: int) -> types.User:
        """Возвращает данные пользователя по его id.
        Если пользователь не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def get_user_by_name(self, username: str) -> types.User:
        """Возвращает данные пользователя по его нику.
        Если пользователь не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def iter_users(self, filters: Optional[Dict[str, Any]] = None) -> Iterator[List[types.User]]:
        """По очереди yield'ит всех существующих пользователей. Если указаны
        фильтры, то с учётом их ограничений. Должны быть реализованы следующие
        фильтры:

        * ``user_id__lt``: id меньше указанного;
        * ``user_id__lte``: id меньше указанного или равен ему;
        * ``user_id__gt``: id больше указанного;
        * ``user_id__gte``: id больше указанного или равен ему.
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

            if filters and 'user_id__lt' in filters:
                if user.id >= filters['user_id__lt']:
                    continue
            if filters and 'user_id__lte' in filters:
                if user.id > filters['user_id__lte']:
                    continue
            if filters and 'user_id__gt' in filters:
                if user.id <= filters['user_id__gt']:
                    continue
            if filters and 'user_id__gte' in filters:
                if user.id < filters['user_id__gte']:
                    continue

            yield [user]

    def get_username_by_user_id(self, user_id: int) -> str:
        """Возвращает имя пользователя по его id."""
        return self.get_user_by_id(user_id).username

    def get_users_limits(self, filters: Optional[Dict[str, Any]] = None) -> types.UsersLimits:
        """Возвращает статистику о всех существующих пользователях. Если
        указаны фильтры, то с учётом их ограничений.
        """
        raise NotImplementedError

    # Блоги

    def get_blog_by_id(self, blog_id: int) -> types.Blog:
        """Возвращает данные блога по его id.
        Если пост не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def get_blog_by_slug(self, slug: str) -> types.Blog:
        """Возвращает данные блога по его slug (url-имя блога,
        которое используется в ссылках).
        """
        raise NotImplementedError

    def get_blog_status_by_id(self, blog_id: Optional[int]) -> int:
        """Возвращает статус блога по его id. 0 - открытый блог,
        1 - закрытый, 2 - полузакрытый.

        blog_id = None означает личный блог, и для него всегда должен
        возвращаться ноль (личные блоги всегда открытые).
        """
        if blog_id is None:
            return 0
        return self.get_blog_by_id(blog_id).status

    def get_blog_status_by_slug(self, slug: Optional[str]) -> int:
        """Возвращает статус блога по его slug. 0 - открытый блог,
        1 - закрытый, 2 - полузакрытый.

        Пустой slug означает личный блог, и для него всегда должнен
        возвращаться ноль (личные блоги всегда открытые).
        """
        if not slug:
            return 0
        return self.get_blog_by_slug(slug).status

    def get_blog_id_by_slug(self, slug: str) -> int:
        """Возвращает id блога по его slug."""
        return self.get_blog_by_slug(slug).id

    def get_blog_id_of_post(self, post_id: int) -> Optional[int]:
        """Возвращает id блога, в котором находится указанный пост.
        Если в личном блоге, то None.
        """
        return self.get_post_by_id(post_id).blog_id

    def iter_blogs(self, filters: Optional[Dict[str, Any]] = None) -> Iterator[List[types.Blog]]:
        """По очереди yield'ит все существующие блоги. Если указаны фильтры,
        то с учётом их ограничений. Должны быть реализованы следующие фильтры:

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

            if filters and 'blog_id__lt' in filters:
                if blog.id >= filters['blog_id__lt']:
                    continue
            if filters and 'blog_id__lte' in filters:
                if blog.id > filters['blog_id__lte']:
                    continue
            if filters and 'blog_id__gt' in filters:
                if blog.id <= filters['blog_id__gt']:
                    continue
            if filters and 'blog_id__gte' in filters:
                if blog.id < filters['blog_id__gte']:
                    continue

            yield [blog]

    def get_blogs_limits(self, filters: Optional[Dict[str, Any]] = None) -> types.BlogsLimits:
        """Возвращает статистику о всех существующих блогах. Если указаны
        фильтры, то с учётом их ограничений.
        """
        raise NotImplementedError

    # Посты (опционально с комментами)

    def get_post_by_id(self, post_id: int, with_comments: bool = False) -> types.Post:
        """Возвращает словарь с данными поста по его id.
        Если пост не найден, выбрасывает ошибку DataNotFound.

        Если указано with_comments=True, то должно ещё присутствовать
        поле comments со списком комментариев (сортировка не определена);
        формат комментария см. в справке get_comment_by_id.
        """
        raise NotImplementedError

    def iter_posts(self, with_comments: bool = False, filters: Optional[Dict[str, Any]] = None) -> Iterator[List[types.Post]]:
        """По очереди yield'ит все существующие посты. Если указаны фильтры,
        то с учётом их ограничений. Должны быть реализованы следующие фильтры:

        * ``post_id__lt``: id меньше указанного;
        * ``post_id__lte``: id меньше указанного или равен ему;
        * ``post_id__gt``: id больше указанного;
        * ``post_id__gte``: id больше указанного или равен ему;
        * ``created_at__lt``, ``created_at__lte``, ``created_at__gt``,
          ``created_at__gte``: аналогично для времени создания поста (datetime)
        """
        stat = self.get_posts_limits(filters=filters)
        if not stat.count:
            return
        assert stat.first_id is not None and stat.last_id is not None

        for post_id in range(stat.first_id, stat.last_id + 1):
            try:
                post = self.get_post_by_id(post_id, with_comments)
            except DataNotFound:
                continue

            if filters and 'post_id__lt' in filters:
                if post.id >= filters['post_id__lt']:
                    continue
            if filters and 'post_id__lte' in filters:
                if post.id > filters['post_id__lte']:
                    continue
            if filters and 'post_id__gt' in filters:
                if post.id <= filters['post_id__gt']:
                    continue
            if filters and 'post_id__gte' in filters:
                if post.id < filters['post_id__gte']:
                    continue

            if filters and 'created_at__lt' in filters:
                if not post.created_at or post.created_at >= filters['created_at__lt']:
                    continue
            if filters and 'created_at__lte' in filters:
                if not post.created_at or post.created_at > filters['created_at__lte']:
                    continue
            if filters and 'created_at__gt' in filters:
                if not post.created_at or post.created_at <= filters['created_at__gt']:
                    continue
            if filters and 'created_at__gte' in filters:
                if not post.created_at or post.created_at < filters['created_at__gte']:
                    continue

            yield [post]

    def get_posts_limits(self, filters: Optional[Dict[str, Any]] = None) -> types.PostsLimits:
        """Возвращает статистику о всех существующих постах. Если указаны
        фильтры, то с учётом их ограничений.
        """
        raise NotImplementedError

    # Комменты

    def get_comment_by_id(self, comment_id: int) -> types.Comment:
        """Возвращает словарь с данными комментария по его id.
        Если комментарий не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def get_post_comments(self, post_id: int) -> List[types.Comment]:
        """Возвращает список комментариев для данного поста.
        Если пост не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def iter_comments(self, filters: Optional[Dict[str, Any]] = None) -> Iterator[List[types.Comment]]:
        """По очереди yield'ит все существующие комменты. Если указаны фильтры,
        то с учётом их ограничений. Должны быть реализованы следующие фильтры:

        * ``comment_id__lt``: id меньше указанного;
        * ``comment_id__lte``: id меньше указанного или равен ему;
        * ``comment_id__gt``: id больше указанного;
        * ``comment_id__gte``: id больше указанного или равен ему;
        * ``post_id__lt``, ``post_id__lte``, ``post_id__gt``, ``post_id__gte``:
          аналогично, но для id поста, которому принадлежит коммент;
        * ``created_at__lt``, ``created_at__lte``, ``created_at__gt``,
          ``created_at__gte``: аналогично для времени создания коммента
          (datetime)
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

            if filters and 'comment_id__lt' in filters:
                if comment.id >= filters['comment_id__lt']:
                    continue
            if filters and 'comment_id__lte' in filters:
                if comment.id > filters['comment_id__lte']:
                    continue
            if filters and 'comment_id__gt' in filters:
                if comment.id <= filters['comment_id__gt']:
                    continue
            if filters and 'comment_id__gte' in filters:
                if comment.id < filters['comment_id__gte']:
                    continue

            if filters and 'post_id__lt' in filters:
                if comment.id >= filters['post_id__lt']:
                    continue
            if filters and 'post_id__lte' in filters:
                if comment.id > filters['post_id__lte']:
                    continue
            if filters and 'post_id__gt' in filters:
                if comment.id <= filters['post_id__gt']:
                    continue
            if filters and 'post_id__gte' in filters:
                if comment.id < filters['post_id__gte']:
                    continue

            if filters and 'created_at__lt' in filters:
                if not comment.created_at or comment.created_at >= filters['created_at__lt']:
                    continue
            if filters and 'created_at__lte' in filters:
                if not comment.created_at or comment.created_at > filters['created_at__lte']:
                    continue
            if filters and 'created_at__gt' in filters:
                if not comment.created_at or comment.created_at <= filters['created_at__gt']:
                    continue
            if filters and 'created_at__gte' in filters:
                if not comment.created_at or comment.created_at < filters['created_at__gte']:
                    continue

            yield [comment]

    def get_comments_limits(self, filters: Optional[Dict[str, Any]] = None) -> types.CommentsLimits:
        """Возвращает статистику о всех существующих комментах. Если указаны
        фильтры, то с учётом их ограничений.
        """
        raise NotImplementedError
