#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Optional, List, Dict, Tuple, Any, Set, Iterable, TextIO
from datetime import date, datetime, timedelta

from tabun_stat import utils
from tabun_stat.processors.base import BaseProcessor

from tabun_stat.stat import TabunStat


class ActivityProcessor(BaseProcessor):
    def __init__(self, periods: Iterable[int] = (1, 7, 30)) -> None:
        super().__init__()
        self.periods = tuple(periods)  # type: Tuple[int, ...]
        self._max_period = max(self.periods)  # type: int

        # Список активности по дням. Каждый элемент — множество айдишников
        # пользователей, активных в этот день
        # (первое множество — юзеры с постами, второе — с комментами)
        self._activity = []  # type: List[Tuple[Set[int], Set[int]]]
        self._last_day = None  # type: Optional[date]
        self._users_with_posts = set()  # type: Set[int]
        self._users_with_comments = set()  # type: Set[int]
        self._fp = None  # type: Optional[TextIO]

    def start(
        self, stat: TabunStat,
        min_date: Optional[datetime] = None, max_date: Optional[datetime] = None
    ) -> None:
        super().start(stat, min_date, max_date)
        assert self.stat
        self._fp = open(os.path.join(self.stat.destination, 'activity.csv'), 'w', encoding='utf-8')

        header = ['Дата']
        for period in self.periods:
            if period == 1:
                header.append('Активны в этот день')
            else:
                header.append('Активны в последние {} дней'.format(period))

        self._fp.write(utils.csvline(*header))

    def process_post(self, post: Dict[str, Any]) -> None:
        self._put_activity(0, post['author_id'], post['created_at_local'])

    def process_comment(self, comment: Dict[str, Any]) -> None:
        self._put_activity(1, comment['author_id'], comment['created_at_local'])

    def _put_activity(self, idx: int, user_id: int, created_at_local: datetime) ->None:
        # idx: 0 - пост, 1 - коммент

        assert self.stat

        # Накатываем часовой пояс пользователя для определения местной границы суток
        day = created_at_local.date()

        if self._last_day is None:
            # Если это первый вызов _put_activity
            self._last_day = day
            self._activity.append((set(), set()))
            assert len(self._activity) == 1

        else:
            assert day >= self._last_day  # TabunStat нам гарантирует это

            # Если день изменился, то сливаем всю прошлую статистику
            # в результат и добавляем следующий день на обработку
            while day > self._last_day:
                self._flush_activity()
                self._last_day += timedelta(days=1)
                # Удаляем лишние старые дни и добавляем новый день
                if self._max_period > 1:
                    self._activity = self._activity[-(self._max_period - 1):] + [(set(), set())]
                else:
                    self._activity = [(set(), set())]

        self._activity[-1][idx].add(user_id)

    def _flush_activity(self) -> None:
        stat = [str(self._last_day)]  # type: List[Any]

        for period in self.periods:
            # Собираем все id за последние period дней
            all_users = set()  # type: Set[int]

            for a, b in self._activity[-period:]:
                all_users = all_users | a | b
                self._users_with_posts = self._users_with_posts | a
                self._users_with_comments = self._users_with_comments | b

            stat.append(len(all_users))

        # И пишем собранные числа в статистику
        assert self._fp
        self._fp.write(utils.csvline(*stat))

    def stop(self) -> None:
        assert self.stat

        if self._last_day is not None:
            self._flush_activity()
        if self._fp:
            self._fp.close()
            self._fp = None

        users_all = self.stat.source.get_users_limits()['count']

        with open(os.path.join(self.stat.destination, 'active_users.txt'), 'w', encoding='utf-8') as fp:
            fp.write('Всего юзеров: {}\n'.format(users_all))
            fp.write('Юзеров с постами: {}\n'.format(len(self._users_with_posts)))
            fp.write('Юзеров с комментами: {}\n'.format(len(self._users_with_comments)))
            fp.write('Юзеров с постами и комментами: {}\n'.format(len(self._users_with_posts & self._users_with_comments)))
            fp.write('Юзеров с постами или комментами: {}\n'.format(len(self._users_with_posts | self._users_with_comments)))
            fp.write('Юзеров без постов и без комментов: {}\n'.format(users_all - len(self._users_with_posts | self._users_with_comments)))
            fp.write('Юзеров с постами, но без комментов: {}\n'.format(len(self._users_with_posts - self._users_with_comments)))
            fp.write('Юзеров с комментами, но без постов: {}\n'.format(len(self._users_with_comments - self._users_with_posts)))

        super().stop()
