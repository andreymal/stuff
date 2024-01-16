# pylint: disable=unused-argument

import typing

from tabun_stat import types

if typing.TYPE_CHECKING:
    from tabun_stat.stat import TabunStat


class BaseProcessor:
    def __init__(self) -> None:
        self._used = False

    def start(self, stat: "TabunStat") -> None:
        if self._used:
            raise RuntimeError("Cannot use processor many times")
        self._used = True

    def stop(self, stat: "TabunStat") -> None:
        assert self._used

    def begin_users(self, stat: "TabunStat", limits: types.UsersLimits) -> None:
        pass

    def process_user(self, stat: "TabunStat", user: types.User) -> None:
        pass

    def end_users(self, stat: "TabunStat", limits: types.UsersLimits) -> None:
        pass

    def begin_blogs(self, stat: "TabunStat", limits: types.BlogsLimits) -> None:
        pass

    def process_blog(self, stat: "TabunStat", blog: types.Blog) -> None:
        pass

    def end_blogs(self, stat: "TabunStat", limits: types.BlogsLimits) -> None:
        pass

    def begin_messages(
        self,
        stat: "TabunStat",
        posts_limits: types.PostsLimits,
        comments_limits: types.CommentsLimits,
    ) -> None:
        pass

    def process_post(self, stat: "TabunStat", post: types.Post) -> None:
        pass

    def process_comment(self, stat: "TabunStat", comment: types.Comment) -> None:
        pass

    def end_messages(
        self,
        stat: "TabunStat",
        posts_limits: types.PostsLimits,
        comments_limits: types.CommentsLimits,
    ) -> None:
        pass
