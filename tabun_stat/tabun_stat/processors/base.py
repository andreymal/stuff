import typing
from datetime import datetime

from tabun_stat import types

if typing.TYPE_CHECKING:
    from tabun_stat.stat import TabunStat


class BaseProcessor:
    def __init__(self) -> None:
        self.stat: "TabunStat" | None = None
        self.min_date: datetime | None = None
        self.max_date: datetime | None = None
        self._used = False

    def start(
        self,
        stat: "TabunStat",
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ) -> None:
        if self._used:
            raise RuntimeError("Cannot use processor many times")
        self._used = True

        assert stat
        self.stat = stat
        self.min_date = min_date
        self.max_date = max_date

    def stop(self) -> None:
        self.stat = None
        self.min_date = None
        self.max_date = None
        assert self._used

    def begin_users(self, stat: types.UsersLimits) -> None:
        pass

    def process_user(self, user: types.User) -> None:
        pass

    def end_users(self, stat: types.UsersLimits) -> None:
        pass

    def begin_blogs(self, stat: types.BlogsLimits) -> None:
        pass

    def process_blog(self, blog: types.Blog) -> None:
        pass

    def end_blogs(self, stat: types.BlogsLimits) -> None:
        pass

    def begin_messages(self, stat_posts: types.PostsLimits, stat_comments: types.CommentsLimits) -> None:
        pass

    def process_post(self, post: types.Post) -> None:
        pass

    def process_comment(self, comment: types.Comment) -> None:
        pass

    def end_messages(self, stat_posts: types.PostsLimits, stat_comments: types.CommentsLimits) -> None:
        pass
