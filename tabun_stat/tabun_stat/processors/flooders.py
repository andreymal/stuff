import os
from datetime import datetime

from tabun_stat import types, utils
from tabun_stat.datasource.base import DataNotFound
from tabun_stat.processors.base import BaseProcessor


class FloodersProcessor(BaseProcessor):
    def __init__(
        self,
        date_ranges: list[tuple[datetime, datetime]] | None = None,
    ):
        super().__init__()

        # Здесь статистика по годам

        # С закрытыми блогами
        self._flooders_all_posts: dict[int, dict[int, int]] = {}
        self._flooders_all_comments: dict[int, dict[int, int]] = {}

        # Только открытые и полузакрытые
        self._flooders_public_posts: dict[int, dict[int, int]] = {}
        self._flooders_public_comments: dict[int, dict[int, int]] = {}

        # Здесь статистика по указанным в конфиге диапазонам дат
        self._date_ranges: list[tuple[datetime, datetime]] = date_ranges or []

        # Число в ключах словаря — индекс диапазона в списке date_ranges
        self._flooders_all_posts_ranges: dict[int, dict[int, int]] = {}
        self._flooders_all_comments_ranges: dict[int, dict[int, int]] = {}

        self._flooders_public_posts_ranges: dict[int, dict[int, int]] = {}
        self._flooders_public_comments_ranges: dict[int, dict[int, int]] = {}

    def _put(
        self,
        obj_year: dict[int, dict[int, int]],
        obj_ranges: dict[int, dict[int, int]],
        date_local: datetime,
        author_id: int,
        count: int = 1,
    ) -> None:
        year = date_local.year
        if year not in obj_year:
            obj_year[year] = {}
        try:
            obj_year[year][author_id] += count
        except KeyError:
            obj_year[year][author_id] = count

        for i, (dt_from, dt_to) in enumerate(self._date_ranges):
            if dt_from <= date_local < dt_to:
                if i not in obj_ranges:
                    obj_ranges[i] = {}
                try:
                    obj_ranges[i][author_id] += count
                except KeyError:
                    obj_ranges[i][author_id] = count

    def _union_years(self, obj: dict[int, dict[int, int]]) -> dict[int, int]:
        result: dict[int, int] = {}

        for x in obj.values():
            for user_id, count in x.items():
                if user_id not in result:
                    result[user_id] = count
                else:
                    result[user_id] += count

        return result

    def process_post(self, post: types.Post) -> None:
        assert self.stat
        assert post.created_at_local is not None

        self._put(
            self._flooders_all_posts, self._flooders_all_posts_ranges, post.created_at_local, post.author_id
        )

        blog_status = post.blog_status
        if blog_status in (0, 2):
            self._put(
                self._flooders_public_posts,
                self._flooders_public_posts_ranges,
                post.created_at_local,
                post.author_id,
            )

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat
        assert comment.created_at_local is not None

        try:
            if comment.post_id is None:
                raise DataNotFound
            blog_id = self.stat.source.get_blog_id_of_post(comment.post_id)
        except DataNotFound:
            self.stat.log(0, f"WARNING: flooders: comment {comment.id} for unknown post {comment.post_id}")
            return

        self._put(
            self._flooders_all_comments,
            self._flooders_all_comments_ranges,
            comment.created_at_local,
            comment.author_id,
        )

        blog_status = self.stat.source.get_blog_status_by_id(blog_id)
        if blog_status in (0, 2):
            self._put(
                self._flooders_public_comments,
                self._flooders_public_comments_ranges,
                comment.created_at_local,
                comment.author_id,
            )

    def stop(self) -> None:
        assert self.stat

        # Сохраняем статистику по годам

        years = set(self._flooders_all_posts) | set(self._flooders_all_comments)
        years = years | set(self._flooders_public_posts) | set(self._flooders_public_comments)
        if not years:
            return
        years_min = min(years)
        years_max = max(years)

        for year in range(years_min, years_max + 1):
            # Непубличную отдельно
            self.save_stat(
                f"flooders_{year}.csv",
                self._flooders_all_posts.get(year) or {},
                self._flooders_all_comments.get(year) or {},
            )
            # Публичную отдельно
            self.save_stat(
                f"flooders_public_{year}.csv",
                self._flooders_public_posts.get(year) or {},
                self._flooders_public_comments.get(year) or {},
            )

        # И то же самое для всех годов в сумме

        flooders_all_posts = self._union_years(self._flooders_all_posts)
        flooders_all_comments = self._union_years(self._flooders_all_comments)
        flooders_public_posts = self._union_years(self._flooders_public_posts)
        flooders_public_comments = self._union_years(self._flooders_public_comments)

        self.save_stat("flooders_all.csv", flooders_all_posts, flooders_all_comments)
        self.save_stat("flooders_public_all.csv", flooders_public_posts, flooders_public_comments)

        # А также по тем диапазонам, которые указаны в конфиге
        for i, (dt_from, dt_to) in enumerate(self._date_ranges):
            from_str = dt_from.strftime("%Y-%m-%d_%H-%M-%S")
            to_str = dt_to.strftime("%Y-%m-%d_%H-%M-%S")

            # Непубличную отдельно
            self.save_stat(
                f"flooders_{from_str}__{to_str}.csv",
                self._flooders_all_posts_ranges.get(i) or {},
                self._flooders_all_comments_ranges.get(i) or {},
            )
            # Публичную отдельно
            self.save_stat(
                f"flooders_public_{from_str}__{to_str}.csv",
                self._flooders_public_posts_ranges.get(i) or {},
                self._flooders_public_comments_ranges.get(i) or {},
            )

        super().stop()

    def save_stat(self, filename: str, stat_posts: dict[int, int], stat_comments: dict[int, int]) -> None:
        assert self.stat

        stat: dict[int, list[int]] = {}

        for user_id, count in stat_posts.items():
            if user_id not in stat:
                stat[user_id] = [0, 0]
            stat[user_id][0] = count

        for user_id, count in stat_comments.items():
            if user_id not in stat:
                stat[user_id] = [0, 0]
            stat[user_id][1] = count

        items = sorted(stat.items(), key=lambda x: x[1][0] + x[1][1], reverse=True)

        with open(os.path.join(self.stat.destination, filename), "w", encoding="utf-8") as fp:
            fp.write(utils.csvline("ID юзера", "Пользователь", "Сколько постов", "Сколько комментов"))

            for user_id, (posts_count, comments_count) in items:
                fp.write(
                    utils.csvline(
                        user_id,
                        self.stat.source.get_username_by_user_id(user_id),
                        posts_count,
                        comments_count,
                    )
                )
