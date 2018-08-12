#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Dict, Any
from datetime import date, timedelta

from tabun_stat import utils
from tabun_stat.processors.base import BaseProcessor


class RegistrationsProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()

        self._stat = {}  # type: Dict[date, int]
        self._stat_gte_minus20 = {}  # type: Dict[date, int]
        self._stat_gte_plus20 = {}  # type: Dict[date, int]

    def process_user(self, user: Dict[str, Any]) -> None:
        day = user['registered_at_local'].date()

        if day not in self._stat:
            self._stat[day] = 0
        self._stat[day] += 1

        if user['rating'] >= -20.0:
            if day not in self._stat_gte_minus20:
                self._stat_gte_minus20[day] = 0
            self._stat_gte_minus20[day] += 1

        if user['rating'] >= 20.0:
            if day not in self._stat_gte_plus20:
                self._stat_gte_plus20[day] = 0
            self._stat_gte_plus20[day] += 1

    def end_users(self, stat: Dict[str, Any]) -> None:
        assert self.stat

        if not self._stat:
            return

        day = min(self._stat)
        max_day = max(self._stat)

        with open(os.path.join(self.stat.destination, 'registrations.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline(
                'Дата',
                'Новые пользователи',
                'Всего пользователей',
                'Всего с рейтингом больше -20',
                'Всего с рейтингом больше +20'
            ))

            all_users = 0
            all_users_gte_minus20 = 0
            all_users_gte_plus20 = 0

            while day <= max_day:
                # Слава костылям
                if day not in self._stat and (day.year < 2011 or day.year == 2011 and day.month < 8):
                    day += timedelta(days=1)
                    continue

                all_users += self._stat.get(day, 0)
                all_users_gte_minus20 += self._stat_gte_minus20.get(day, 0)
                all_users_gte_plus20 += self._stat_gte_plus20.get(day, 0)

                fp.write(utils.csvline(
                    day,
                    self._stat.get(day, 0),
                    all_users,
                    all_users_gte_minus20,
                    all_users_gte_plus20
                ))

                day += timedelta(days=1)
