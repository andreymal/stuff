import os
import re
from typing import Dict, Any, List
from datetime import datetime

from tabun_stat import types, utils
from tabun_stat.datasource.base import DataNotFound
from tabun_stat.processors.base import BaseProcessor


img_re = re.compile('<img[^>]+src="([^"]+)".*>', flags=re.U | re.I)


class ImagesProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()

        self._stat = {}  # type: Dict[str, Dict[str, Any]]
        self._images_list = []  # type: List[str]

        self._hosts = {}  # type: Dict[str, List[int]]
        self._hosts2 = {}  # type: Dict[str, List[int]]

    def process_post(self, post: types.Post) -> None:
        self._process(post.body, post.blog_status, post.created_at)

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat

        try:
            if comment.post_id is None:
                raise DataNotFound
            blog_id = self.stat.source.get_blog_id_of_post(comment.post_id)
        except DataNotFound:
            self.stat.log(0, f'WARNING: images: comment {comment.id} for unknown post {comment.post_id}')
            return

        blog_status = self.stat.source.get_blog_status_by_id(blog_id)
        self._process(comment.body, blog_status, comment.created_at)

    def _get_host(self, url: str) -> str:
        # https://example.com:80/path → example.com:80/path
        f = url.find('://')
        if f >= 0:
            host = url[f + 3:]
        elif url.startswith('//'):
            host = url[2:]
        else:
            host = url

        # example.com:80/path → example.com:80
        host = host.split('/', 1)[0]

        # example.com:80 → example.com
        host = host.split(':', 1)[0]

        return host

    def _get_host2(self, url: str) -> str:
        host = self._get_host(url)

        # a.b.c.d.e → d.e
        while host.count('.') > 1:
            host = host[host.find('.') + 1:]
        return host

    def _process(self, body: str, blog_status: int, created_at: datetime) -> None:
        body = body.strip()
        if '<' not in body:
            return

        images = set(img_re.findall(body))
        is_public = blog_status in (0, 2)

        for img in images:
            if not img:
                continue
            # Если картинка попалась первый раз, создаём статистику
            if img not in self._stat:
                self._images_list.append(img)
                stat = {}  # type: Dict[str, Any]
                stat = {
                    # Хост вида foo.bar.example.com
                    'host': self._get_host(img),
                    # Хост вида example.com
                    'host2': self._get_host2(img),

                    # Статистика с учётом закрытых блогов
                    'first_date': created_at,
                    'last_date': None,
                    'count': 0,

                    # Статитстика только по открытым и полузакрытым
                    'first_public_date': created_at if is_public else None,
                    'last_public_date': None,
                    'public_count': 0,
                }
                self._stat[img] = stat

                if stat['host']:
                    if stat['host'] not in self._hosts:
                        self._hosts[stat['host']] = [0, 0]
                    self._hosts[stat['host']][0] += 1

                if stat['host2']:
                    if stat['host2'] not in self._hosts2:
                        self._hosts2[stat['host2']] = [0, 0]
                    self._hosts2[stat['host2']][0] += 1

            else:
                stat = self._stat[img]

            stat['last_date'] = created_at
            stat['count'] += 1
            if is_public:
                stat['last_public_date'] = created_at
                stat['public_count'] += 1

            if stat['host']:
                self._hosts[stat['host']][1] += 1

            if stat['host2']:
                self._hosts2[stat['host2']][1] += 1

    def stop(self) -> None:
        assert self.stat

        with open(os.path.join(self.stat.destination, 'images.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline(
                'Картинка',
                'Первое исп-е',
                'Первое исп-е на внешке',
                'Последнее исп-е',
                'Последнее исп-е на внешке',
                'Сколько раз',
                'Сколько раз на внешке'
            ))

            for img in self._images_list:
                data = self._stat[img]
                fp.write(utils.csvline(
                    img,
                    data['first_date'],
                    data['first_public_date'] or '',
                    data['last_date'],
                    data['last_public_date'] or '',
                    data['count'],
                    data['public_count']
                ))

        with open(os.path.join(self.stat.destination, 'images_hosts.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline('Хост', 'Число ссылок', 'Число использований'))

            items = sorted(self._hosts.items(), key=lambda x: x[1][1], reverse=True)
            for h, c in items:
                assert c[1] >= c[0]
                fp.write(utils.csvline(h, c[0], c[1]))

        with open(os.path.join(self.stat.destination, 'images_hosts2.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline('Хост', 'Число ссылок', 'Число использований'))

            items = sorted(self._hosts2.items(), key=lambda x: x[1][1], reverse=True)
            for h, c in items:
                assert c[1] >= c[0]
                fp.write(utils.csvline(h, c[0], c[1]))

        super().stop()
