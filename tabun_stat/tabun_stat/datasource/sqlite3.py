#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import date, datetime
from typing import Optional, Dict, Tuple, List, Any, Iterable

from tabun_stat.datasource.base import BaseDataSource, DataNotFound


class Sqlite3DataSource(BaseDataSource):
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn = None  # type: Any

        # Кэш статусов блогов по их id
        self._blog_status_by_id = {}  # type: Dict[int, int]
        # Кэш статусов блогов по их slug
        self._blog_status_by_slug = {}  # type: Dict[str, int]
        # Кэш айдишников блогов по slug
        self._blog_ids = {}  # type: Dict[str, int]
        # Кэш блогов постов
        self._post_blogs = {}  # type: Dict[int, Optional[int]]
        # Кэш имён пользователей по их id
        self._usernames = {}  # type: Dict[int, str]
        self.reconnect()

    def destroy(self) -> None:
        # При уничтожении отключаемся от БД
        if self._conn:
            self._conn.close()
            self._conn = None

    def reconnect(self) -> None:
        # Если нас просят переподключиться, но БД уже подключена,
        # то отключаем её
        if self._conn:
            self._conn.close()
            self._conn = None

        try:
            self._conn = sqlite3.connect(self._path)
        except Exception:
            self._conn = None
            raise

        # Сразу предзагружаем кэши
        self._fetch_blog_info()

    def _fetch_blog_info(self) -> None:
        blogs_status = self.fetchall_dict('select blog_id, slug, status from blogs')
        self._blog_status_by_id = {
            x['blog_id']: x['status']
            for x in blogs_status
        }
        self._blog_status_by_slug = {
            x['slug']: x['status']
            for x in blogs_status
        }
        self._blog_ids = {x['slug']: x['blog_id'] for x in blogs_status}

    def execute(self, sql: str, args: tuple = ()) -> Any:
        cur = self._conn.cursor()
        cur.execute(sql, args)
        return cur

    def fetchall(self, sql: str, args: tuple = ()) -> List[tuple]:
        return self.execute(sql, args).fetchall()

    def fetchall_dict(self, sql: str, args: tuple = ()) -> List[Dict[str, Any]]:
        c = self.execute(sql, args)
        result_tuple = c.fetchall()
        result = []

        colnames = [x[0] for x in c.description]
        for x in result_tuple:
            item = {name: value for name, value in zip(colnames, x)}
            result.append(item)

        return result

    # Табунчане

    def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        item = self.fetchall_dict('select * from users where user_id = ?', (user_id,))
        if not item:
            raise DataNotFound
        return self._userdict(item[0])

    def get_user_by_name(self, username: str) -> Dict[str, Any]:
        item = self.fetchall_dict('select * from users where username = ?', (username,))
        if not item:
            raise DataNotFound
        return self._userdict(item[0])

    def iter_users(self, filters: Optional[Dict[str, Any]] = None) -> Iterable[List[Dict[str, Any]]]:
        stat = self.get_users_limits(filters=filters)
        if not stat['count']:
            return

        where, where_args = build_filter('user', filters, prefix=' AND ')

        last_id = stat['first_id'] - 1
        while last_id < stat['last_id']:
            users = self.fetchall_dict(
                'select * from users where user_id >= ?{} order by user_id limit 1000'.format(where),
                (last_id + 1,) + where_args,
            )
            if not users:
                break

            yield [self._userdict(x) for x in users]
            last_id = users[-1]['user_id']

    def get_users_limits(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        where, where_args = build_filter('user', filters, prefix=' where ')

        return self.fetchall_dict(
            'select min(user_id) first_id, max(user_id) last_id, count(user_id) `count` '
            'from users' + where, where_args
        )[0]

    def get_username_by_user_id(self, user_id: int) -> str:
        if user_id not in self._usernames:
            return self.get_user_by_id(user_id)['username']
        return self._usernames[user_id]

    def _userdict(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        # Попутно заполняем кэш юзернеймов
        self._usernames[raw_item['user_id']] = raw_item['username']

        item = raw_item.copy()
        item['registered_at'] = datetime.strptime(item['registered_at'], '%Y-%m-%d %H:%M:%S')
        if item['birthday']:
            item['birthday'] = datetime.strptime(item['birthday'], '%Y-%m-%d').date()
        return item

    # Блоги

    def get_blog_by_id(self, blog_id: int) -> Dict[str, Any]:
        item = self.fetchall_dict('select * from blogs where blog_id = ?', (blog_id,))
        if not item:
            raise DataNotFound
        return self._blogdict(item[0])

    def get_blog_by_slug(self, slug: str) -> Dict[str, Any]:
        item = self.fetchall_dict('select * from blogs where slug = ?', (slug,))
        if not item:
            raise DataNotFound
        return self._blogdict(item[0])

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
            self._post_blogs[post_id] = self.get_post_by_id(post_id)['blog_id']
        return self._post_blogs[post_id]

    def iter_blogs(self, filters: Optional[Dict[str, Any]] = None) -> Iterable[List[Dict[str, Any]]]:
        stat = self.get_blogs_limits(filters=filters)
        if not stat['count']:
            return

        where, where_args = build_filter('blog', filters, prefix=' AND ')

        last_id = stat['first_id'] - 1
        while last_id < stat['last_id']:
            blogs = self.fetchall_dict(
                'select * from blogs where blog_id >= ?{} order by blog_id limit 1000'.format(where),
                (last_id + 1,) + where_args,
            )
            if not blogs:
                break

            yield [self._blogdict(x) for x in blogs]
            last_id = blogs[-1]['blog_id']

    def get_blogs_limits(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        where, where_args = build_filter('blog', filters, prefix=' where ')

        return self.fetchall_dict(
            'select min(blog_id) first_id, max(blog_id) last_id, count(blog_id) `count` '
            'from blogs' + where, where_args
        )[0]

    def _blogdict(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        item = raw_item.copy()
        item['created_at'] = datetime.strptime(item['created_at'], '%Y-%m-%d %H:%M:%S')
        item['deleted'] = bool(item['deleted'])
        return item

    # Посты (опционально с комментами)

    def get_post_by_id(self, post_id: int, with_comments: bool = False) -> Dict[str, Any]:
        item = self.fetchall_dict('select * from posts where post_id = ?', (post_id,))
        if not item:
            raise DataNotFound
        post = self._postdict(item[0])
        if with_comments:
            post['comments'] = self.get_post_comments(post_id)
        return post

    def iter_posts(self, with_comments: bool = False, filters: Optional[Dict[str, Any]] = None) -> Iterable[List[Dict[str, Any]]]:
        stat = self.get_posts_limits(filters=filters)
        if not stat['count']:
            return

        where, where_args = build_filter('post', filters, prefix=' AND ')

        last_id = stat['first_id'] - 1
        while last_id < stat['last_id']:
            posts = self.fetchall_dict(
                'select * from posts where post_id >= ?{} limit 1000'.format(where),
                (last_id + 1,) + where_args,
            )
            if not posts:
                break
            posts.sort(key=lambda x: x['post_id'])

            comments_dict = None  # type: Optional[Dict[int, List[Dict[str, Any]]]]
            if with_comments:
                comments_dict = {x['post_id']: [] for x in posts}
                comments_list = self.fetchall_dict(
                    'select * from comments where post_id >= ? and post_id <= ?',
                    (posts[0]['post_id'], posts[-1]['post_id'])
                )
                comments_list.sort(key=lambda x: x['comment_id'])
                for c in comments_list:
                    comments_dict[c['post_id']].append(self._commentdict(c))
                del comments_list

            posts_ready = []
            for x in posts:
                post = self._postdict(x)
                if comments_dict is not None:
                    post['comments'] = comments_dict.pop(post['post_id'])
                posts_ready.append(post)

            if posts_ready:
                yield posts_ready

            last_id = posts[-1]['post_id']

    def get_posts_limits(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        where, where_args = build_filter('post', filters, prefix=' where ')

        result = self.fetchall_dict(
            'select min(post_id) first_id, max(post_id) last_id, count(post_id) `count`, '
            'min(created_at) first_created_at, max(created_at) last_created_at '
            'from posts' + where, where_args
        )[0]
        if result['first_created_at'] is not None:
            result['first_created_at'] = datetime.strptime(result['first_created_at'], '%Y-%m-%d %H:%M:%S')
        if result['last_created_at'] is not None:
            result['last_created_at'] = datetime.strptime(result['last_created_at'], '%Y-%m-%d %H:%M:%S')
        return result

    def _postdict(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        # Попутно заполняем кэш блогов
        self._post_blogs[raw_item['post_id']] = raw_item['blog_id'] or None

        item = raw_item.copy()
        item['created_at'] = datetime.strptime(item['created_at'], '%Y-%m-%d %H:%M:%S')
        item['deleted'] = bool(item['deleted'])
        item['draft'] = bool(item['draft'])
        return item

    # Комменты

    def get_comment_by_id(self, comment_id: int) -> Dict[str, Any]:
        item = self.fetchall_dict('select * from comments where comment_id = ?', (comment_id,))
        if not item:
            raise DataNotFound
        post = self._commentdict(item[0])
        return post

    def get_post_comments(self, post_id: int) -> List[Dict[str, Any]]:
        items = self.fetchall_dict(
            'select * from comments where post_id = ?',
            (post_id,)
        )
        items.sort(key=lambda x: x['comment_id'])

        return [self._commentdict(x) for x in items]

    def iter_comments(self, filters: Optional[Dict[str, Any]] = None) -> Iterable[List[Dict[str, Any]]]:
        stat = self.get_comments_limits(filters=filters)
        if not stat['count']:
            return

        where, where_args = build_filter('comment', filters, prefix=' AND ')

        last_id = stat['first_id'] - 1
        while True:
            comments = self.fetchall_dict(
                'select * from comments where comment_id >= ?{} limit 10000'.format(where),
                (last_id + 1,) + where_args,
            )
            if not comments:
                break
            comments.sort(key=lambda x: x['comment_id'])

            yield [self._commentdict(x) for x in comments]
            last_id = comments[-1]['comment_id']

    def get_comments_limits(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        where, where_args = build_filter('comment', filters, prefix=' where ')

        result = self.fetchall_dict(
            'select min(comment_id) first_id, max(comment_id) last_id, count(comment_id) `count`, '
            'min(created_at) first_created_at, max(created_at) last_created_at '
            'from comments' + where, where_args
        )[0]
        if result['first_created_at'] is not None:
            result['first_created_at'] = datetime.strptime(result['first_created_at'], '%Y-%m-%d %H:%M:%S')
        if result['last_created_at'] is not None:
            result['last_created_at'] = datetime.strptime(result['last_created_at'], '%Y-%m-%d %H:%M:%S')
        return result

    def _commentdict(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        item = raw_item.copy()
        item['created_at'] = datetime.strptime(item['created_at'], '%Y-%m-%d %H:%M:%S')
        item['deleted'] = bool(item['deleted'])
        return item


def build_filter(type: str, filters: Optional[Dict[str, Any]] = None, prefix: str = '') -> Tuple[str, tuple]:
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
