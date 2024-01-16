from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


class NicknamesProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self._letters: dict[str, set[int]] = {}

    def process_user(self, stat: TabunStat, user: types.User) -> None:
        c = user.username[0]
        if c not in self._letters:
            self._letters[c] = set()
        self._letters[c].add(user.id)

    def end_users(self, stat: TabunStat, limits: types.UsersLimits) -> None:
        with (stat.destination / "nicknames.csv").open("w", encoding="utf-8") as fp:
            fp.write(utils.csvline("Первая буква ника", "Число пользователей"))
            for c, user_ids in sorted(self._letters.items(), key=lambda x: len(x[1]), reverse=True):
                fp.write(utils.csvline(c, len(user_ids)))
