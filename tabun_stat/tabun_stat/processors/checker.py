#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional, Dict, Any
from datetime import datetime

from tabun_stat.processors.base import BaseProcessor

from tabun_stat.stat import TabunStat


class CheckerProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self._last_post = None  # type: Optional[Dict[str, Any]]
        self._last_comment = None  # type: Optional[Dict[str, Any]]

    def start(
        self, stat: TabunStat,
        min_date: Optional[datetime] = None, max_date: Optional[datetime] = None
    ) -> None:
        super().start(stat, min_date, max_date)
        self._last_post = None
        self._last_comment = None

    def stop(self) -> None:
        self._last_post = None
        self._last_comment = None
        super().stop()

    def process_user(self, user: Dict[str, Any]) -> None:
        pass

    def process_blog(self, blog: Dict[str, Any]) -> None:
        pass

    def process_post(self, post: Dict[str, Any]) -> None:
        assert self.stat

        if self._last_post is not None:
            if post['created_at'] < self._last_post['created_at']:
                self.stat.log(
                    0, 'WARNING: next post {} {} is from past! (prev post is {} {})'.format(
                        post['post_id'], post['created_at'],
                        self._last_post['post_id'], self._last_post['created_at']
                    )
                )
        self._last_post = post

    def process_comment(self, comment: Dict[str, Any]) -> None:
        assert self.stat

        if self._last_comment is not None:
            if comment['created_at'] < self._last_comment['created_at']:
                self.stat.log(
                    0, 'WARNING: next comment {} {} is from past! (prev comment is {} {})'.format(
                        comment['comment_id'], comment['created_at'],
                        self._last_comment['comment_id'], self._last_comment['created_at']
                    )
                )
        self._last_comment = comment
