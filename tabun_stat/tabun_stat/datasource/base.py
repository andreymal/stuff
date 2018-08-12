#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional, Iterable, List, Dict, Any


__all__ = ['DataNotFound', 'BaseDataSource']


class DataNotFound(Exception):
    pass


class BaseDataSource:
    def destroy(self) -> None:
        pass

    def _filter_object(self, type: str, obj: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> bool:
        # pylint: disable=W0622,C0325

        if type not in ('user', 'blog', 'post', 'comment'):
            raise ValueError('Invalid filter type: {!r}'.format(type))

        if not filters:
            return True

        ok = True

        for k, v in filters.items():
            if '__' in k:
                key, act = k.rsplit('__', 1)
            else:
                key, act = k, '?'

            if type == 'user' and key not in ('user_id',):
                raise ValueError('Invalid {} filter: {!r}'.format(type, k))
            if type == 'blog' and key not in ('blog_id',):
                raise ValueError('Invalid {} filter: {!r}'.format(type, k))
            if type == 'post' and key not in ('post_id', 'time'):
                raise ValueError('Invalid {} filter: {!r}'.format(type, k))
            if type == 'comment' and key not in ('comment_id', 'post_id', 'time'):
                raise ValueError('Invalid {} filter: {!r}'.format(type, k))

            if act == 'lt':
                if not (obj[key] < v):
                    ok = False
            elif act == 'lte':
                if not (obj[key] <= v):
                    ok = False
            elif act == 'gt':
                if not (obj[key] > v):
                    ok = False
            elif act == 'gte':
                if not (obj[key] >= v):
                    ok = False
            else:
                raise ValueError('Invalid {} filter: {!r}'.format(type, k))

        return ok

    # Табунчане

    def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        """Возвращает словарь с данными пользователя по его id.
        Если пользователь не найден, выбрасывает ошибку DataNotFound.

        Поля: user_id (int), username (str), realname (str),
        skill (float), rating (float), gender ('M', 'F' или None),
        birthday (date или None), registered_at (datetime или None),
        description (str)
        """
        raise NotImplementedError

    def get_user_by_name(self, username: str) -> Dict[str, Any]:
        """Возвращает словарь с данными пользователя по его нику.
        Если пользователь не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def iter_users(self, filters: Optional[Dict[str, Any]] = None) -> Iterable[List[Dict[str, Any]]]:
        """По очереди yield'ит всех существующих пользователей. Если указаны
        фильтры, то с учётом их ограничений. Должны быть реализованы следующие
        фильтры:

        * ``user_id__lt``: id меньше указанного;
        * ``user_id__lte``: id меньше указанного или равен ему;
        * ``user_id__gt``: id больше указанного;
        * ``user_id__gte``: id больше указанного или равен ему.
        """

        stat = self.get_users_limits(filters=filters)

        for user_id in range(stat['first_id'], stat['last_id'] + 1):
            try:
                user = self.get_user_by_id(user_id)
            except DataNotFound:
                continue

            if filters and 'user_id__lt' in filters:
                if user['user_id'] >= filters['user_id__lt']:
                    continue
            if filters and 'user_id__lte' in filters:
                if user['user_id'] > filters['user_id__lte']:
                    continue
            if filters and 'user_id__gt' in filters:
                if user['user_id'] <= filters['user_id__gt']:
                    continue
            if filters and 'user_id__gte' in filters:
                if user['user_id'] < filters['user_id__gte']:
                    continue

            yield [user]

    def get_username_by_user_id(self, user_id: int) -> str:
        """Возвращает имя пользователя по его id."""
        return self.get_user_by_id(user_id)['username']

    def get_users_limits(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Возвращает статистику о всех существующих пользователях. Если
        указаны фильтры, то с учётом их ограничений. Результат — вот такой
        словарь:

        * ``count`` (int) — общее число пользователей;
        * ``first_id`` (int или None) — самый маленький id (если есть);
        * ``last_id`` (int или None) — самый большой id (если есть).
        """
        raise NotImplementedError

    # Блоги

    def get_blog_by_id(self, blog_id: int) -> Dict[str, Any]:
        """Возвращает словарь с данными блога по его id.
        Если пост не найден, выбрасывает ошибку DataNotFound.

        Поля: blog_id (int), slug (str), name (str),
        creator_id (int, id юзера), rating (float), status (int, 0 - открытый,
        1 - закрытый, 2 - полузакрытый), description (str), vote_count (int),
        created_at (datetime), deleted (bool)
        """
        raise NotImplementedError

    def get_blog_by_slug(self, slug: str) -> Dict[str, Any]:
        """Возвращает словарь с данными блога по его slug (url-имя блога,
        которое используется в ссылках).
        """
        raise NotImplementedError

    def get_blog_status_by_id(self, blog_id: Optional[int]) -> int:
        """Возвращает статус блога по его id. 0 - открытый блог,
        1 - закрытый, 2 - полузакрытый.

        blog_id = None означает личный блог, и для него всегда должнен
        возвращаться ноль (личные блоги всегда открытые).
        """
        if blog_id is None:
            return 0
        return self.get_blog_by_id(blog_id)['status']

    def get_blog_status_by_slug(self, slug: Optional[str]) -> int:
        """Возвращает статус блога по его slug. 0 - открытый блог,
        1 - закрытый, 2 - полузакрытый.

        Пустой slug означает личный блог, и для него всегда должнен
        возвращаться ноль (личные блоги всегда открытые).
        """
        if not slug:
            return 0
        return self.get_blog_by_slug(slug)['status']

    def get_blog_id_by_slug(self, slug: str) -> int:
        """Возвращает id блога по его slug."""
        return self.get_blog_by_slug(slug)['blog_id']

    def get_blog_id_of_post(self, post_id: int) -> Optional[int]:
        """Возвращает id блога, в котором находится указанный пост.
        Если в личном блоге, то None.
        """
        return self.get_post_by_id(post_id)['blog_id']

    def iter_blogs(self, filters: Optional[Dict[str, Any]] = None) -> Iterable[List[Dict[str, Any]]]:
        """По очереди yield'ит все существующие блоги. Если указаны фильтры,
        то с учётом их ограничений. Должны быть реализованы следующие фильтры:

        * ``blog_id__lt``: id меньше указанного;
        * ``blog_id__lte``: id меньше указанного или равен ему;
        * ``blog_id__gt``: id больше указанного;
        * ``blog_id__gte``: id больше указанного или равен ему.
        """
        stat = self.get_blogs_limits(filters=filters)

        for blog_id in range(stat['first_id'], stat['last_id'] + 1):
            try:
                blog = self.get_blog_by_id(blog_id)
            except DataNotFound:
                continue

            if filters and 'blog_id__lt' in filters:
                if blog['blog_id'] >= filters['blog_id__lt']:
                    continue
            if filters and 'blog_id__lte' in filters:
                if blog['blog_id'] > filters['blog_id__lte']:
                    continue
            if filters and 'blog_id__gt' in filters:
                if blog['blog_id'] <= filters['blog_id__gt']:
                    continue
            if filters and 'blog_id__gte' in filters:
                if blog['blog_id'] < filters['blog_id__gte']:
                    continue

            yield [blog]

    def get_blogs_limits(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Возвращает статистику о всех существующих блогах. Если указаны
        фильтры, то с учётом их ограничений. Результат — вот такой словарь:

        * ``count`` (int) — общее число блогов;
        * ``first_id`` (int или None) — самый маленький id (если есть);
        * ``last_id`` (int или None) — самый большой id (если есть).
        """
        raise NotImplementedError

    # Посты (опционально с комментами)

    def get_post_by_id(self, post_id: int, with_comments: bool = False) -> Dict[str, Any]:
        """Возвращает словарь с данными поста по его id.
        Если пост не найден, выбрасывает ошибку DataNotFound.

        Если указано with_comments=True, то должно ещё присутствовать
        поле comments со списком комментариев (сортировка не определена);
        формат комментария см. в справке get_comment_by_id.

        Поля: post_id (int), created_at (datetime), blog_id (int; для личного
        блога None), blog_status (0, 1 или 2; для личных блогов всегда 0),
        author_id (int, id пользователя), title (str), vote_count (int),
        vote_value (int или None, если неизвестно), body (str),
        favorites_count (int), deleted (bool), draft (bool)
        """
        raise NotImplementedError

    def iter_posts(self, with_comments: bool = False, filters: Optional[Dict[str, Any]] = None) -> Iterable[List[Dict[str, Any]]]:
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

        for post_id in range(stat['first_id'], stat['last_id'] + 1):
            try:
                post = self.get_post_by_id(post_id, with_comments)
            except DataNotFound:
                continue

            if filters and 'post_id__lt' in filters:
                if post['post_id'] >= filters['post_id__lt']:
                    continue
            if filters and 'post_id__lte' in filters:
                if post['post_id'] > filters['post_id__lte']:
                    continue
            if filters and 'post_id__gt' in filters:
                if post['post_id'] <= filters['post_id__gt']:
                    continue
            if filters and 'post_id__gte' in filters:
                if post['post_id'] < filters['post_id__gte']:
                    continue

            if filters and 'created_at__lt' in filters:
                if not post['created_at'] or post['created_at'] >= filters['created_at__lt']:
                    continue
            if filters and 'created_at__lte' in filters:
                if not post['created_at'] or post['created_at'] > filters['created_at__lte']:
                    continue
            if filters and 'created_at__gt' in filters:
                if not post['created_at'] or post['created_at'] <= filters['created_at__gt']:
                    continue
            if filters and 'created_at__gte' in filters:
                if not post['created_at'] or post['created_at'] < filters['created_at__gte']:
                    continue

            yield [post]

    def get_posts_limits(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Возвращает статистику о всех существующих постах. Если указаны
        фильтры, то с учётом их ограничений. Результат — вот такой словарь:

        * ``count`` (int) — общее число постов;
        * ``first_id`` (int или None) — самый маленький id;
        * ``last_id`` (int или None) — самый большой id;
        * ``first_created_at`` (datetime или None) — самая ранняя дата поста;
        * ``last_created_at`` (datetime или None) — самая поздняя дата поста.
        """
        raise NotImplementedError

    # Комменты

    def get_comment_by_id(self, comment_id: int) -> Dict[str, Any]:
        """Возвращает словарь с данными комментария по его id.
        Если комментарий не найден, выбрасывает ошибку DataNotFound.

        Поля: comment_id (int), post_id (int или None для комментов-сирот),
        parent_id (int или None), author_id (int), created_at (datetime),
        vote_value (int), body (str), deleted (bool), favorites_count (int).
        """
        raise NotImplementedError

    def get_post_comments(self, post_id: int) -> List[Dict[str, Any]]:
        """Возвращает список комментариев для данного поста.
        Если пост не найден, выбрасывает ошибку DataNotFound.
        """
        raise NotImplementedError

    def iter_comments(self, filters: Optional[Dict[str, Any]] = None) -> Iterable[List[Dict[str, Any]]]:
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

        for comment_id in range(stat['first_id'], stat['last_id'] + 1):
            try:
                comment = self.get_comment_by_id(comment_id)
            except DataNotFound:
                continue

            if filters and 'comment_id__lt' in filters:
                if comment['comment_id'] >= filters['comment_id__lt']:
                    continue
            if filters and 'comment_id__lte' in filters:
                if comment['comment_id'] > filters['comment_id__lte']:
                    continue
            if filters and 'comment_id__gt' in filters:
                if comment['comment_id'] <= filters['comment_id__gt']:
                    continue
            if filters and 'comment_id__gte' in filters:
                if comment['comment_id'] < filters['comment_id__gte']:
                    continue

            if filters and 'post_id__lt' in filters:
                if comment['post_id'] >= filters['post_id__lt']:
                    continue
            if filters and 'post_id__lte' in filters:
                if comment['post_id'] > filters['post_id__lte']:
                    continue
            if filters and 'post_id__gt' in filters:
                if comment['post_id'] <= filters['post_id__gt']:
                    continue
            if filters and 'post_id__gte' in filters:
                if comment['post_id'] < filters['post_id__gte']:
                    continue

            if filters and 'created_at__lt' in filters:
                if not comment['created_at'] or comment['created_at'] >= filters['created_at__lt']:
                    continue
            if filters and 'created_at__lte' in filters:
                if not comment['created_at'] or comment['created_at'] > filters['created_at__lte']:
                    continue
            if filters and 'created_at__gt' in filters:
                if not comment['created_at'] or comment['created_at'] <= filters['created_at__gt']:
                    continue
            if filters and 'created_at__gte' in filters:
                if not comment['created_at'] or comment['created_at'] < filters['created_at__gte']:
                    continue

            yield [comment]

    def get_comments_limits(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Возвращает статистику о всех существующих комментах. Если указаны
        фильтры, то с учётом их ограничений. Результат — вот такой словарь:

        * ``count`` (int) — общее число комментов;
        * ``first_id`` (int или None) — самый маленький id;
        * ``last_id`` (int или None) — самый большой id;
        * ``first_created_at`` (datetime или None) — самая ранняя дата
          коммента;
        * ``last_created_at`` (datetime или None) — самая поздняя дата
          коммента.
        """
        raise NotImplementedError
