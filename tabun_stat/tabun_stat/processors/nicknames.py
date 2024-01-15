import os
from typing import Dict, Set

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor


class NicknamesProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self._letters = {}  # type: Dict[str, Set[int]]

    def process_user(self, user: types.User) -> None:
        c = user.username[0]
        if c not in self._letters:
            self._letters[c] = set()
        self._letters[c].add(user.id)

    def stop(self) -> None:
        assert self.stat

        with open(os.path.join(self.stat.destination, 'nicknames.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline('Первая буква ника', 'Число пользователей'))
            for c, user_ids in sorted(self._letters.items(), key=lambda x: len(x[1]), reverse=True):
                fp.write(utils.csvline(c, len(user_ids)))

        super().stop()
