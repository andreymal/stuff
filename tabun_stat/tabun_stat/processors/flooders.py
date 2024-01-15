import os
from typing import Dict, List

from tabun_stat import types, utils
from tabun_stat.datasource.base import DataNotFound
from tabun_stat.processors.base import BaseProcessor


class FloodersProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()

        # С закрытыми блогами
        self._flooders_all_posts = {}  # type: Dict[int, Dict[int, int]]
        self._flooders_all_comments = {}  # type: Dict[int, Dict[int, int]]

        # Только открытые и полузакрытые
        self._flooders_public_posts = {}  # type: Dict[int, Dict[int, int]]
        self._flooders_public_comments = {}  # type: Dict[int, Dict[int, int]]

    def _put(self, obj: Dict[int, Dict[int, int]], year: int, author_id: int, count: int = 1) -> None:
        if year not in obj:
            obj[year] = {}
        try:
            obj[year][author_id] += count
        except KeyError:
            obj[year][author_id] = count

    def _union_years(self, obj: Dict[int, Dict[int, int]]) -> Dict[int, int]:
        result = {}  # type: Dict[int, int]

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
        year = post.created_at_local.year

        self._put(self._flooders_all_posts, year, post.author_id)

        blog_status = post.blog_status
        if blog_status in (0, 2):
            self._put(self._flooders_public_posts, year, post.author_id)

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat
        assert comment.created_at_local is not None
        year = comment.created_at_local.year

        try:
            if comment.post_id is None:
                raise DataNotFound
            blog_id = self.stat.source.get_blog_id_of_post(comment.post_id)
        except DataNotFound:
            self.stat.log(0, f'WARNING: flooders: comment {comment.id} for unknown post {comment.post_id}')
            return

        self._put(self._flooders_all_comments, year, comment.author_id)

        blog_status = self.stat.source.get_blog_status_by_id(blog_id)
        if blog_status in (0, 2):
            self._put(self._flooders_public_comments, year, comment.author_id)

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
                'flooders_{}.csv'.format(year),
                self._flooders_all_posts.get(year) or {},
                self._flooders_all_comments.get(year) or {},
            )
            # Публичную отдельно
            self.save_stat(
                'flooders_public_{}.csv'.format(year),
                self._flooders_public_posts.get(year) or {},
                self._flooders_public_comments.get(year) or {},
            )

        # И то же самое для всех годов в сумме

        flooders_all_posts = self._union_years(self._flooders_all_posts)
        flooders_all_comments = self._union_years(self._flooders_all_comments)
        flooders_public_posts = self._union_years(self._flooders_public_posts)
        flooders_public_comments = self._union_years(self._flooders_public_comments)

        self.save_stat( 'flooders_all.csv', flooders_all_posts, flooders_all_comments)
        self.save_stat( 'flooders_public_all.csv', flooders_public_posts, flooders_public_comments)

        super().stop()

    def save_stat(
        self,
        filename: str,
        stat_posts: Dict[int, int],
        stat_comments: Dict[int, int]
    ) -> None:
        assert self.stat

        stat: Dict[int, List[int]] = {}

        for user_id, count in stat_posts.items():
            if user_id not in stat:
                stat[user_id] = [0, 0]
            stat[user_id][0] = count

        for user_id, count in stat_comments.items():
            if user_id not in stat:
                stat[user_id] = [0, 0]
            stat[user_id][1] = count

        items = sorted(stat.items(), key=lambda x: x[1][0] + x[1][1], reverse=True)

        with open(os.path.join(self.stat.destination, filename), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline('ID юзера', 'Пользователь', 'Сколько постов', 'Сколько комментов'))

            for user_id, (posts_count, comments_count) in items:
                fp.write(utils.csvline(
                    user_id,
                    self.stat.source.get_username_by_user_id(user_id),
                    posts_count,
                    comments_count,
                ))
