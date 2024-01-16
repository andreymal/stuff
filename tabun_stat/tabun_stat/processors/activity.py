from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import IO, Sequence

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


@dataclass(slots=True)
class ActivityStat:
    # Минимальный рейтинг пользователей, которые считаются в текущем объекте
    min_rating: float | None = None

    # Список активности по дням. Каждый элемент — множество айдишников
    # пользователей, активных в этот день
    # (количество хранимых дней ограничено максимальным периодом в опции periods)
    # Первый set — пользователи, писавшие посты; второй — писавшие комменты
    activity: list[tuple[set[int], set[int]]] = field(default_factory=list)

    # Айдишники юзеров с постами за всё время
    users_with_posts: set[int] = field(default_factory=set)

    # Айдишники юзеров с комментами за всё время
    users_with_comments: set[int] = field(default_factory=set)

    # Файл, в который будет записываться статистика по окончании очередного дня
    fp: IO[str] | None = None


class ActivityProcessor(BaseProcessor):
    def __init__(
        self,
        *,
        periods: Sequence[int] = (1, 7, 30),
        rating_thresholds: Sequence[float] = (0.0,),
    ):
        super().__init__()
        self.periods = periods
        self._max_period = max(self.periods)

        self._stats = []
        for min_rating in [None] + list(rating_thresholds):
            self._stats.append(ActivityStat(min_rating=min_rating))

        self._user_ratings: dict[int, float] = {}  # {user_id: rating}
        self._last_day: date | None = None

    def start(
        self,
        stat: TabunStat,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ) -> None:
        super().start(stat, min_date, max_date)
        assert self.stat

        header = ["Дата"]
        for period in self.periods:
            if period == 1:
                header.append("Активны в этот день")
            else:
                header.append(f"Активны в последние {period} дней")

        for item in self._stats:
            filename = "activity.csv"
            if item.min_rating is not None:
                filename = f"activity_{item.min_rating:.2f}.csv"
            item.fp = (self.stat.destination / filename).open("w", encoding="utf-8")
            item.fp.write(utils.csvline(*header))

    def process_user(self, user: types.User) -> None:
        # Собираем рейтинги пользователей
        self._user_ratings[user.id] = user.rating

    def process_post(self, post: types.Post) -> None:
        assert self.stat
        assert post.created_at_local is not None

        if post.author_id in self._user_ratings:
            rating = self._user_ratings[post.author_id]
        else:
            self.stat.log(0, f"WARNING: activity: unknown author {post.author_id} of post {post.id}")
            rating = 0.0

        self._put_activity(0, post.author_id, post.created_at_local, rating)

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat
        assert comment.created_at_local is not None

        if comment.author_id in self._user_ratings:
            rating = self._user_ratings[comment.author_id]
        else:
            self.stat.log(0, f"WARNING: activity: unknown author {comment.author_id} of comment {comment.id}")
            rating = 0.0

        self._put_activity(1, comment.author_id, comment.created_at_local, rating)

    def _put_activity(self, idx: int, user_id: int, created_at_local: datetime, rating: float) -> None:
        # idx: 0 - пост, 1 - коммент

        assert self.stat

        day = created_at_local.date()

        if self._last_day is None:
            # Если это первый вызов _put_activity
            self._last_day = day
            for item in self._stats:
                item.activity.append((set(), set()))
                assert len(item.activity) == 1

        else:
            assert day >= self._last_day  # TabunStat нам гарантирует это

            # Если день изменился, то сливаем всю прошлую статистику
            # в результат и добавляем следующий день на обработку
            while day > self._last_day:
                for item in self._stats:
                    self._flush_activity(item)
                self._last_day += timedelta(days=1)
                # Удаляем лишние старые дни и добавляем новый день
                for item in self._stats:
                    if self._max_period > 1:
                        del item.activity[: -(self._max_period - 1)]
                        item.activity.append((set(), set()))
                    else:
                        item.activity[0][0].clear()
                        item.activity[0][1].clear()

        for item in self._stats:
            if item.min_rating is None or rating >= item.min_rating:
                item.activity[-1][idx].add(user_id)

    def _flush_activity(self, item: ActivityStat) -> None:
        row: list[object] = [str(self._last_day)]

        for period in self.periods:
            # Собираем все id за последние period дней
            all_users: set[int] = set()

            for p, c in item.activity[-period:]:
                all_users = all_users | p | c
                item.users_with_posts = item.users_with_posts | p
                item.users_with_comments = item.users_with_comments | c

            row.append(len(all_users))

        # И пишем собранные числа в статистику
        assert item.fp is not None
        item.fp.write(utils.csvline(*row))

    def stop(self) -> None:
        assert self.stat

        for item in self._stats:
            if self._last_day is not None:
                self._flush_activity(item)
            if item.fp is not None:
                item.fp.close()
                item.fp = None

            if item.min_rating is not None:
                filename = f"active_users_{item.min_rating:.2f}.txt"
                users_all = len([x for x in self._user_ratings.values() if x >= item.min_rating])
                header = f"# Статистика пользователей с рейтингом {item.min_rating:.2f} и больше\n\n"
            else:
                filename = "active_users.txt"
                users_all = len(self._user_ratings)
                header = "# Статистика пользователей с любым рейтингом\n\n"

            with (self.stat.destination / filename).open("w", encoding="utf-8") as fp:
                fp.write(header)

                fp.write(f"Всего юзеров: {users_all}\n")
                fp.write(f"Юзеров с постами: {len(item.users_with_posts)}\n")
                fp.write(f"Юзеров с комментами: {len(item.users_with_comments)}\n")
                fp.write(
                    f"Юзеров с постами и комментами: {len(item.users_with_posts & item.users_with_comments)}\n"
                )
                fp.write(
                    f"Юзеров с постами или комментами: {len(item.users_with_posts | item.users_with_comments)}\n"
                )
                fp.write(
                    f"Юзеров без постов и без комментов: {users_all - len(item.users_with_posts | item.users_with_comments)}\n"
                )
                fp.write(
                    f"Юзеров с постами, но без комментов: {len(item.users_with_posts - item.users_with_comments)}\n"
                )
                fp.write(
                    f"Юзеров с комментами, но без постов: {len(item.users_with_comments - item.users_with_posts)}\n"
                )

        super().stop()
