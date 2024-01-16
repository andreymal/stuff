from datetime import date, timedelta
from typing import Sequence

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


class RegistrationsProcessor(BaseProcessor):
    def __init__(
        self,
        *,
        start_date: date = date(2011, 8, 8),
        rating_thresholds: Sequence[float] = (
            -20.0,
            0.0,
            0.01,
            20.0,
            100.0,
            1000.0,
            10000.0,
        ),
    ):
        super().__init__()
        self.start_date = start_date

        # Все пользователи
        # {день: число регистраций в этот день}
        self._stat: dict[date, int] = {}

        # Пользователи, имеющие указанный рейтинг на момент подсчёта статистики
        # [(рейтинг, {день: число регистраций в этот день})]
        self._stat_by_rating: list[tuple[float, dict[date, int]]] = [(r, {}) for r in rating_thresholds]

    def process_user(self, stat: TabunStat, user: types.User) -> None:
        assert user.registered_at_local is not None
        day = user.registered_at_local.date()

        if day not in self._stat:
            self._stat[day] = 0
        self._stat[day] += 1

        for r, rstat in self._stat_by_rating:
            if user.rating >= r:
                if day not in rstat:
                    rstat[day] = 0
                rstat[day] += 1

    def end_users(self, stat: TabunStat, limits: types.UsersLimits) -> None:
        if not self._stat:
            return

        day = min(self._stat)
        max_day = max(self._stat)

        with (stat.destination / "registrations.csv").open("w", encoding="utf-8") as fp:
            headers = ["Дата", "Новые пользователи", "Всего пользователей"]
            for r, _ in self._stat_by_rating:
                headers.append(f"Всего с рейтингом ≥ {r:0.2f}")

            fp.write(utils.csvline(*headers))

            all_users = 0
            all_users_by_rating = [0] * len(self._stat_by_rating)

            while day <= max_day:
                all_users += self._stat.get(day, 0)
                for i, (_, rdict) in enumerate(self._stat_by_rating):
                    all_users_by_rating[i] += rdict.get(day, 0)

                if day >= self.start_date:
                    row = [day, self._stat.get(day, 0), all_users]
                    row.extend(all_users_by_rating)
                    fp.write(utils.csvline(*row))

                day += timedelta(days=1)
