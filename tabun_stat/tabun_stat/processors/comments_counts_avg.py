import os
from datetime import date, timedelta
from typing import Any

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor


class CommentsCountsAvgProcessor(BaseProcessor):
    def __init__(
        self,
        collect_empty_days: bool = False,
    ):
        super().__init__()

        self.collect_empty_days = collect_empty_days

        self._last_day = date(1970, 1, 1)

        self._counts: dict[tuple[int, int], list[int]] = {}
        self._days: dict[tuple[int, int], int] = {}

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat
        assert comment.created_at_local is not None
        day = comment.created_at_local.date()
        hour = comment.created_at_local.hour

        # Если это самый первый коммент, поступивший на обработку, то
        # инициализиуем всю статистику
        if self._last_day.year == 1970:
            self._last_day = day
            self._counts = {(day.year, day.month): [0] * 24}
            self._days = {(day.year, day.month): 1}

        # Если день сменился, то готовим статистику для нового дня
        assert day >= self._last_day
        while day != self._last_day:
            if self.collect_empty_days:
                # Благодаря циклу while дни без комментов будут учитываться
                self._last_day += timedelta(days=1)
            else:
                # ...или не учитываться, если в конфиге отключено
                self._last_day = day

            mon = (self._last_day.year, self._last_day.month)
            if mon not in self._counts:
                self._counts[mon] = [0] * 24
                self._days[mon] = 0
            self._days[mon] += 1

        self._counts[(day.year, day.month)][hour] += 1

    def stop(self) -> None:
        assert self.stat

        # Считаем статистику за всё время...
        counts_all = [0] * 24
        days_all = 0

        # ...и по годам...
        counts_year: dict[int, list[int]] = {}
        days_year: dict[int, int] = {}

        # ...в одном цикле
        for (year, monn), stat in self._counts.items():
            days = self._days[(year, monn)]

            if year not in counts_year:
                counts_year[year] = [0] * 24
                days_year[year] = 0

            days_all += days
            days_year[year] += days

            for hour, cnt in enumerate(stat):
                counts_all[hour] += cnt
                counts_year[year][hour] += cnt

        last_months = sorted(self._counts)[-2:]

        # Собираем CSV-заголовок
        header = [f"Час ({str(self.stat.timezone)})", "За всё время"]
        for year in sorted(counts_year):
            header.append(f"{year} год")
        for mon in last_months:
            header.append(f"{mon[0]:04d}-{mon[1]:02d}")

        with open(
            os.path.join(self.stat.destination, "comments_counts_avg.csv"), "w", encoding="utf-8"
        ) as fp:
            fp.write(utils.csvline(*header))

            for hour in range(24):
                line: list[Any] = [hour]

                # За всё время
                line.append("{:.2f}".format(counts_all[hour] / (days_all or 1)))

                # И по годам
                for year in sorted(counts_year):
                    line.append("{:.2f}".format(counts_year[year][hour] / (days_year.get(year) or 1)))

                # И за два последних месяца
                for mon in last_months:
                    line.append("{:.2f}".format(self._counts[mon][hour] / (self._days.get(mon) or 1)))

                fp.write(utils.csvline(*line))

        super().stop()
