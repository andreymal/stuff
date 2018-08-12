#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import math
from typing import Dict, Any, Iterable

from tabun_stat import utils
from tabun_stat.processors.base import BaseProcessor


class UsersRatingsProcessor(BaseProcessor):
    def __init__(self, steps: Iterable[int] = (10, 100)) -> None:
        super().__init__()

        self._ratings = {}  # type: Dict[int, Dict[int, int]]
        self._zero = 0  # Число пользователей с ровно нулевым рейтингом
        for step in steps:
            self._ratings[step] = {}

    def process_user(self, user: Dict[str, Any]) -> None:
        for step in self._ratings:
            step_vote = int(math.floor(user['rating'] / step) * step)
            if step_vote not in self._ratings[step]:
                self._ratings[step][step_vote] = 0
            self._ratings[step][step_vote] += 1

        if user['rating'] == 0.0:
            self._zero += 1

    def end_users(self, stat: Dict[str, Any]) -> None:
        assert self.stat

        for step in self._ratings:
            with open(os.path.join(self.stat.destination, 'users_ratings_{}.csv'.format(step)), 'w', encoding='utf-8') as fp:
                fp.write(utils.csvline('Рейтинг', 'Число пользователей'))

                step_vote = min(self._ratings[step])
                vmax = max(self._ratings[step])

                while step_vote <= vmax:
                    count = self._ratings[step].get(step_vote, 0)

                    x1 = '{:.2f}'.format(step_vote)
                    x2 = '{:.2f}'.format(round(step_vote + (step - 0.01), 2))
                    fp.write(utils.csvline(
                        x1 + ' – ' + x2,
                        count
                    ))

                    step_vote += step

        with open(os.path.join(self.stat.destination, 'users_ratings_zero.txt'), 'w', encoding='utf-8') as fp:
            fp.write('{}\n'.format(self._zero))
