from datetime import date, datetime, timedelta
from typing import IO

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


class OldfagsProcessor(BaseProcessor):
    default_age_days: dict[int, str] = {
        7: "Аккаунты ≤ 7 дней",
        30: "Аккаунты от 8 до 30 дней",
        60: "Аккаунты от 31 до 60 дней",
        90: "Аккаунты от 61 до 90 дней",
        180: "Аккаунты от 91 до 180 дней",
        365: "Аккаунты от 181 дня до 1 года",
        365 * 2: "Аккаунты до 2 лет",
        365 * 3: "Аккаунты до 3 лет",
        365 * 4: "Аккаунты до 4 лет",
        365 * 5: "Аккаунты до 5 лет",
        365 * 6: "Аккаунты до 6 лет",
        365 * 7: "Аккаунты до 7 лет",
        365 * 8: "Аккаунты до 8 лет",
        365 * 9: "Аккаунты до 9 лет",
        365 * 10: "Аккаунты до 10 лет",
    }

    def __init__(
        self,
        *,
        age_days: dict[int, str] | None = None,
        label_max: str = "Аккаунты от 10 лет",
        age_base_date: datetime | None = None,
        dump_user_list_for_months: list[date] | None = None,
    ):
        super().__init__()

        if age_days is None:
            age_days = self.default_age_days
        self._label_max = label_max
        self._age_base_date = age_base_date
        self._dump_user_list_for_months = dump_user_list_for_months or []

        self._age_days: list[int] = []
        self._age_labels: list[str] = []
        for age, label in sorted(age_days.items(), key=lambda x: x[0]):
            self._age_days.append(age)
            self._age_labels.append(label)

        self._regdates: dict[int, datetime] = {}
        self._user_ratings: dict[int, float] = {}

        self._mon: date | None = None  # День не используется и всегда должен быть 1

        # Все блоги
        self._counts = [0] * (len(age_days) + 1)
        self._counted_users: set[int] = set()

        # Только открытые и полузакрытые блоги
        self._public_counts = [0] * (len(age_days) + 1)
        self._public_counted_users: set[int] = set()

        self._fp: IO[str] | None = None
        self._fp_sum: IO[str] | None = None

        self._warned_posts: set[int] = set()

        if self._age_base_date is not None and self._age_base_date.tzinfo is None:
            raise ValueError("age_base_date must be aware datetime")

    def start(
        self,
        stat: TabunStat,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ) -> None:
        super().start(stat, min_date, max_date)
        assert self.stat

        header = ["Месяц"]
        header.extend(self._age_labels)
        header.append(self._label_max)

        suffix = ""
        if self._age_base_date:
            suffix = self._age_base_date.strftime("_rel_%Y-%m-%d")

        self._fp = (stat.destination / f"oldfags{suffix}.csv").open("w", encoding="utf-8")
        self._fp.write(utils.csvline(*header))

        self._fp_sum = (stat.destination / f"oldfags{suffix}_sum.csv").open("w", encoding="utf-8")
        self._fp_sum.write(utils.csvline(*header))

    def process_user(self, user: types.User) -> None:
        assert user.registered_at_local is not None
        self._regdates[user.id] = user.registered_at_local
        self._user_ratings[user.id] = user.rating

    def process_post(self, post: types.Post) -> None:
        self._put_activity(
            post.author_id,
            post.created_at,
            public=post.blog_status in (0, 2),
        )

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat

        if comment.post_id is None or comment.blog_status is None:
            if comment.post_id is None or comment.post_id not in self._warned_posts:
                self.stat.log(
                    0,
                    f"WARNING: oldfags: comment {comment.id} for unknown post {comment.post_id},",
                    "marking as private",
                )
            if comment.post_id is not None:
                self._warned_posts.add(comment.post_id)
            public = False
        else:
            public = comment.blog_status in (0, 2)

        self._put_activity(
            comment.author_id,
            comment.created_at,
            public=public,
        )

    def _put_activity(self, user_id: int, created_at: datetime, *, public: bool) -> None:
        assert self.stat

        try:
            regdate = self._regdates[user_id].timestamp()
        except KeyError:
            self.stat.log(0, f"WARNING: oldfags: activity from unknown user {user_id}, skipping")
            return

        mon = created_at.date().replace(day=1)
        if mon != self._mon:
            self._flush_activity(mon)

        age_base_ts = (self._age_base_date or created_at).timestamp()
        user_age_days = int(age_base_ts - regdate) // 3600 // 24

        count_idx = len(self._counts) - 1
        for i, max_age_days in enumerate(self._age_days):
            if user_age_days <= max_age_days:
                count_idx = i
                break

        if user_id not in self._counted_users:
            self._counts[count_idx] += 1
            self._counted_users.add(user_id)

        if public and user_id not in self._public_counted_users:
            self._public_counts[count_idx] += 1
            self._public_counted_users.add(user_id)

    def _flush_activity(self, new_mon: date) -> None:
        assert self._fp is not None
        assert self._fp_sum is not None
        assert new_mon.day == 1

        if self._mon is None:
            self._mon = new_mon
            return

        while self._mon != new_mon:
            row: list[object] = [f"{self._mon.year:04d}-{self._mon.month:02d}"]
            row.extend(self._counts)
            self._fp.write(utils.csvline(*row))

            # То же самое, но с суммированием для более удобного рисования графика
            row = [f"{self._mon.year:04d}-{self._mon.month:02d}"]
            s = 0
            for c in self._counts:
                s += c
                row.append(s)
            self._fp_sum.write(utils.csvline(*row))

            # А также полные списки пользователей для запрошенных месяцев
            if self._mon in self._dump_user_list_for_months:
                self._dump_users()

            # Проматываем в цикле while до нужного месяца
            # (такой цикл нужен, чтобы не пропустить месяцы без активности
            # и записать нули в статистику)
            self._mon = (self._mon + timedelta(days=32)).replace(day=1)

            self._counts = [0] * (len(self._age_days) + 1)
            self._counted_users.clear()

            self._public_counts = [0] * (len(self._age_days) + 1)
            self._public_counted_users.clear()

    def _dump_users(self) -> None:
        assert self.stat

        if self._mon is None:
            return

        filename = f"oldfags_list_{self._mon.year:04d}-{self._mon.month:02d}.csv"
        with (self.stat.destination / filename).open("w", encoding="utf-8") as fp:
            fp.write(utils.csvline("ID юзера", "Пользователь", "Дата регистрации", "Рейтинг"))
            for user_id in sorted(self._counted_users, key=lambda u: self._regdates[u]):
                fp.write(
                    utils.csvline(
                        user_id,
                        self.stat.source.get_username_by_user_id(user_id),
                        self._regdates[user_id],
                        f"{self._user_ratings[user_id]:.02f}",
                    )
                )

        filename = f"oldfags_public_list_{self._mon.year:04d}-{self._mon.month:02d}.csv"
        with (self.stat.destination / filename).open("w", encoding="utf-8") as fp:
            fp.write(utils.csvline("ID юзера", "Пользователь", "Дата регистрации", "Рейтинг"))
            for user_id in sorted(self._public_counted_users, key=lambda u: self._regdates[u]):
                fp.write(
                    utils.csvline(
                        user_id,
                        self.stat.source.get_username_by_user_id(user_id),
                        self._regdates[user_id],
                        f"{self._user_ratings[user_id]:.02f}",
                    )
                )

    def stop(self) -> None:
        if self._fp is not None:
            if self._mon is not None:
                self._flush_activity((self._mon + timedelta(days=32)).replace(day=1))
            self._fp.close()
            self._fp = None

        if self._fp_sum is not None:
            self._fp_sum.close()
            self._fp_sum = None

        super().stop()
