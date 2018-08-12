#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Dict, Tuple, Any, Set

from tabun_stat import utils
from tabun_stat.processors.base import BaseProcessor


class BirthdaysProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()

        # {(день, месяц): айдишники пользователей}
        self._birthdays = {}  # type: Dict[Tuple[int, int], Set[int]]

    def process_user(self, user: Dict[str, Any]) -> None:
        if not user['birthday']:
            return

        day = (user['birthday'].day, user['birthday'].month)
        if day not in self._birthdays:
            self._birthdays[day] = set()
        self._birthdays[day].add(user['user_id'])

    def end_users(self, stat: Dict[str, Any]) -> None:
        assert self.stat

        with open(os.path.join(self.stat.destination, 'birthdays.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline('День рождения', 'Число пользователей'))
            for day, user_ids in sorted(self._birthdays.items(), key=lambda x: len(x[1]), reverse=True):
                fp.write(utils.csvline('{:02d}.{:02d}'.format(*day), len(user_ids)))
