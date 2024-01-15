from datetime import datetime

from tabun_stat import types
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


class CheckerProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self._last_post: types.Post | None = None
        self._last_comment: types.Comment | None = None

    def start(
        self,
        stat: TabunStat,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ) -> None:
        super().start(stat, min_date, max_date)
        self._last_post = None
        self._last_comment = None

    def stop(self) -> None:
        self._last_post = None
        self._last_comment = None
        super().stop()

    def process_user(self, user: types.User) -> None:
        pass

    def process_blog(self, blog: types.Blog) -> None:
        pass

    def process_post(self, post: types.Post) -> None:
        assert self.stat

        if self._last_post is not None:
            if post.created_at < self._last_post.created_at:
                self.stat.log(
                    0,
                    "WARNING: next post {} {} is from past! (prev post is {} {})".format(
                        post.id,
                        post.created_at,
                        self._last_post.id,
                        self._last_post.created_at,
                    ),
                )
        self._last_post = post

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat

        if self._last_comment is not None:
            if comment.created_at < self._last_comment.created_at:
                self.stat.log(
                    0,
                    "WARNING: next comment {} {} is from past! (prev comment is {} {})".format(
                        comment.id,
                        comment.created_at,
                        self._last_comment.id,
                        self._last_comment.created_at,
                    ),
                )
        self._last_comment = comment
