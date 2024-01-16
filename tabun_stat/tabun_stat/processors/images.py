import re
from dataclasses import dataclass
from datetime import datetime

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor

img_re = re.compile('<img[^>]+src="([^"]+)".*>', flags=re.U | re.I)


@dataclass(slots=True)
class ImageStat:
    # Хост вида foo.bar.example.com
    host: str
    # Хост вида example.com
    host2: str

    # Статистика с учётом закрытых блогов
    first_date: datetime
    last_date: datetime
    # Число сообщений, в которых использована картинка
    # (дубликаты в пределах одного сообщения не считаются)
    count: int

    # Статитстика только по открытым и полузакрытым
    first_public_date: datetime | None = None
    last_public_date: datetime | None = None
    public_count: int = 0


@dataclass(slots=True)
class HostStat:
    # Сколько уникальных ссылок попалось с этим хостом
    unique_count: int = 0
    unique_public_count: int = 0

    # Сколько всего ссылок
    # (с подсчётом дубликатов из разных сообщений, но
    # дубликаты в пределах одного сообщения не считаются)
    all_count: int = 0
    all_public_count: int = 0


class ImagesProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()

        self._stat: dict[str, ImageStat] = {}
        self._images_list: list[str] = []

        self._hosts: dict[str, HostStat] = {}
        self._hosts2: dict[str, HostStat] = {}

        self._warned_posts: set[int] = set()

    def process_post(self, post: types.Post) -> None:
        public = post.blog_status in (0, 2)
        self._process(post.body, public, post.created_at)

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat

        if comment.post_id is None or comment.blog_status is None:
            if comment.post_id is None or comment.post_id not in self._warned_posts:
                self.stat.log(
                    0,
                    f"WARNING: images: comment {comment.id} for unknown post {comment.post_id},",
                    "marking as private",
                )
            if comment.post_id is not None:
                self._warned_posts.add(comment.post_id)
            public = False
        else:
            public = comment.blog_status in (0, 2)

        self._process(comment.body, public, comment.created_at)

    def _get_host(self, url: str) -> str:
        # https://example.com:80/path → example.com:80/path
        f = url.find("://")
        if f >= 0:
            host = url[f + 3 :]
        elif url.startswith("//"):
            host = url[2:]
        else:
            host = url

        # example.com:80/path → example.com:80
        host = host.split("/", 1)[0]

        # example.com:80 → example.com
        host = host.split(":", 1)[0]

        return host

    def _get_host2(self, url: str) -> str:
        host = self._get_host(url)

        # a.b.c.d.e → d.e
        while host.count(".") > 1:
            host = host[host.find(".") + 1 :]
        return host

    def _process(self, body: str, public: bool, created_at: datetime) -> None:
        body = body.strip()
        if "<" not in body:
            return

        images = utils.drop_duplicates(img_re.findall(body))

        for img in images:
            if not img:
                continue

            try:
                stat = self._stat[img]
            except KeyError:
                # Если картинка попалась первый раз, создаём статистику
                self._images_list.append(img)
                stat = ImageStat(
                    host=self._get_host(img),
                    host2=self._get_host2(img),
                    first_date=created_at,
                    last_date=created_at,
                    count=0,
                    first_public_date=created_at if public else None,
                    last_public_date=None,
                    public_count=0,
                )
                self._stat[img] = stat

                # Считаем число уникальных ссылок с этим хостом

                if stat.host:
                    if stat.host not in self._hosts:
                        self._hosts[stat.host] = HostStat()
                    self._hosts[stat.host].unique_count += 1
                    if public:
                        self._hosts[stat.host].unique_public_count += 1

                if stat.host2:
                    if stat.host2 not in self._hosts2:
                        self._hosts2[stat.host2] = HostStat()
                    self._hosts2[stat.host2].unique_count += 1
                    if public:
                        self._hosts2[stat.host2].unique_public_count += 1

            # Считаем число сообщений, в которых встречается эта картинка

            stat.last_date = created_at
            stat.count += 1
            if public:
                stat.last_public_date = created_at
                stat.public_count += 1

            # Считаем число сообщений, в которых встречается этот хост

            if stat.host:
                self._hosts[stat.host].all_count += 1
                if public:
                    self._hosts[stat.host].all_public_count += 1

            if stat.host2:
                self._hosts2[stat.host2].all_count += 1
                if public:
                    self._hosts2[stat.host2].all_public_count += 1

    def stop(self) -> None:
        assert self.stat

        with (self.stat.destination / "images.csv").open("w", encoding="utf-8") as fp:
            fp.write(
                utils.csvline(
                    "Картинка",
                    "Первое исп-е",
                    "Первое исп-е на внешке",
                    "Последнее исп-е",
                    "Последнее исп-е на внешке",
                    "Сколько раз",
                    "Сколько раз на внешке",
                )
            )

            for img in self._images_list:
                data = self._stat[img]
                fp.write(
                    utils.csvline(
                        img,
                        data.first_date,
                        data.first_public_date or "",
                        data.last_date,
                        data.last_public_date or "",
                        data.count,
                        data.public_count,
                    )
                )

        with (self.stat.destination / "images_hosts.csv").open("w", encoding="utf-8") as fp:
            fp.write(
                utils.csvline(
                    "Хост",
                    "Число уникальных ссылок",
                    "Число уникальных ссылок на внешке",
                    "Общее число использований",
                    "Общее число использований на внешке",
                )
            )

            items = sorted(self._hosts.items(), key=lambda x: x[1].all_count, reverse=True)
            for h, c in items:
                assert c.all_count >= c.unique_count
                assert c.all_public_count >= c.unique_public_count
                fp.write(
                    utils.csvline(h, c.unique_count, c.unique_public_count, c.all_count, c.all_public_count)
                )

        with (self.stat.destination / "images_hosts2.csv").open("w", encoding="utf-8") as fp:
            fp.write(
                utils.csvline(
                    "Хост",
                    "Число уникальных ссылок",
                    "Число уникальных ссылок на внешке",
                    "Общее число использований",
                    "Общее число использований на внешке",
                )
            )

            items = sorted(self._hosts2.items(), key=lambda x: x[1].all_count, reverse=True)
            for h, c in items:
                assert c.all_count >= c.unique_count
                assert c.all_public_count >= c.unique_public_count
                fp.write(
                    utils.csvline(h, c.unique_count, c.unique_public_count, c.all_count, c.all_public_count)
                )

        # Дублируем всё то же самое, но без закрытых блогов

        with (self.stat.destination / "images_public.csv").open("w", encoding="utf-8") as fp:
            fp.write(
                utils.csvline(
                    "Картинка", "Первое исп-е на внешке", "Последнее исп-е на внешке", "Сколько раз на внешке"
                )
            )

            for img in self._images_list:
                data = self._stat[img]
                if data.public_count == 0:
                    continue
                fp.write(
                    utils.csvline(
                        img,
                        data.first_public_date or "",
                        data.last_public_date or "",
                        data.public_count,
                    )
                )

        with (self.stat.destination / "images_public_hosts.csv").open("w", encoding="utf-8") as fp:
            fp.write(
                utils.csvline(
                    "Хост",
                    "Число уникальных ссылок на внешке",
                    "Общее число использований на внешке",
                )
            )

            items = sorted(self._hosts.items(), key=lambda x: x[1].all_count, reverse=True)
            for h, c in items:
                if c.unique_public_count == 0:
                    continue
                fp.write(utils.csvline(h, c.unique_public_count, c.all_public_count))

        with (self.stat.destination / "images_hosts2.csv").open("w", encoding="utf-8") as fp:
            fp.write(
                utils.csvline(
                    "Хост",
                    "Число уникальных ссылок на внешке",
                    "Общее число использований на внешке",
                )
            )

            items = sorted(self._hosts2.items(), key=lambda x: x[1].all_count, reverse=True)
            for h, c in items:
                if c.unique_public_count == 0:
                    continue
                fp.write(utils.csvline(h, c.unique_public_count, c.all_public_count))

        super().stop()
