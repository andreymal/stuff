from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


class BirthdaysProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()

        # {(день, месяц): айдишники пользователей}
        self._birthdays: dict[tuple[int, int], set[int]] = {}

    def process_user(self, stat: TabunStat, user: types.User) -> None:
        if user.birthday is None:
            return

        day = (user.birthday.day, user.birthday.month)
        if day not in self._birthdays:
            self._birthdays[day] = set()
        self._birthdays[day].add(user.id)

    def end_users(self, stat: TabunStat, limits: types.UsersLimits) -> None:
        with (stat.destination / "birthdays.csv").open("w", encoding="utf-8") as fp:
            fp.write(utils.csvline("День рождения", "Число пользователей"))
            for day, user_ids in sorted(self._birthdays.items(), key=lambda x: len(x[1]), reverse=True):
                fp.write(utils.csvline(f"{day[0]:02d}.{day[1]:02d}", len(user_ids)))
