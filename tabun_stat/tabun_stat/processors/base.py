#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import typing
from typing import Optional, Dict, Any
from datetime import datetime

if typing.TYPE_CHECKING:
    from tabun_stat.stat import TabunStat  # pylint: disable=W0611


class BaseProcessor:
    def __init__(self) -> None:
        self.stat = None  # type: Optional['TabunStat']
        self.min_date = None  # type: Optional[datetime]
        self.max_date = None  # type: Optional[datetime]
        self._used = False

    def start(
        self, stat: 'TabunStat',
        min_date: Optional[datetime] = None, max_date: Optional[datetime] = None
    ) -> None:
        if self._used:
            raise RuntimeError('Cannot use processor many times')
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

    def begin_users(self, stat: Dict[str, Any]) -> None:
        pass

    def process_user(self, user: Dict[str, Any]) -> None:
        pass

    def end_users(self, stat: Dict[str, Any]) -> None:
        pass

    def begin_blogs(self, stat: Dict[str, Any]) -> None:
        pass

    def process_blog(self, blog: Dict[str, Any]) -> None:
        pass

    def end_blogs(self, stat: Dict[str, Any]) -> None:
        pass

    def begin_messages(self, stat_posts: Dict[str, Any], stat_comments: Dict[str, Any]) -> None:
        pass

    def process_post(self, post: Dict[str, Any]) -> None:
        pass

    def process_comment(self, comment: Dict[str, Any]) -> None:
        pass

    def end_messages(self, stat_posts: Dict[str, Any], stat_comments: Dict[str, Any]) -> None:
        pass
