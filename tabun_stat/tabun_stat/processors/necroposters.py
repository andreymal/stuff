from dataclasses import dataclass, field
from typing import Sequence

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


@dataclass(slots=True)
class NecroStat:
    # Минимальный рейтинг пользователей, которые считаются в текущем объекте
    min_rating: float | None = None

    # {user_id: кол-во бампов старых постов}
    count_by_user: dict[int, int] = field(default_factory=dict)

    # {user_id: баллы}
    score_by_user: dict[int, int] = field(default_factory=dict)

    def add(self, author_id: int, score: int) -> None:
        try:
            self.count_by_user[author_id] += 1
        except KeyError:
            self.count_by_user[author_id] = 1

        try:
            self.score_by_user[author_id] += score
        except KeyError:
            self.score_by_user[author_id] = score


class NecropostersProcessor(BaseProcessor):
    def __init__(
        self,
        *,
        min_inactivity_days: int = 90,
        authors_are_necroposters: bool = False,
        rating_thresholds: Sequence[float] = (0.0,),
    ):
        super().__init__()
        self.min_inactivity_days = min_inactivity_days
        self.authors_are_necroposters = authors_are_necroposters

        self._stats = []
        for min_rating in [None] + list(rating_thresholds):
            self._stats.append(NecroStat(min_rating=min_rating))

        self._last_activity: dict[int, float] = {}  # {post_id: unix_timestamp}
        self._post_authors: dict[int, int] = {}  # {post_id: author_id}
        self._user_ratings: dict[int, float] = {}  # {user_id: rating}

    def process_user(self, stat: TabunStat, user: types.User) -> None:
        self._user_ratings[user.id] = user.rating

    def process_post(self, stat: TabunStat, post: types.Post) -> None:
        if post.blog_status not in (0, 2):
            # Считать некропостеров в закрытых блогах нет смысла, наверное?
            return

        self._post_authors[post.id] = post.author_id
        self._last_activity[post.id] = post.created_at.timestamp()

    def process_comment(self, stat: TabunStat, comment: types.Comment) -> None:
        if comment.post_id is None or comment.blog_status not in (0, 2):
            return

        # Пост 1 — технический в tbackup
        if comment.post_id == 1:
            return

        tm = comment.created_at.timestamp()

        # Забираем время предыдущей активности в посте
        last_activity = self._last_activity.get(comment.post_id)

        # И записываем текущую активность
        self._last_activity[comment.post_id] = tm

        if last_activity is None:
            # Это может случиться в двух случаях:
            # 1) Посты отсечены настройкой min_date
            # 2) Автор поста добавил комментарии ещё в черновиках перед публикацией
            # В таком случае считаем дату коммента датой первой активности, чтобы считать хоть что-то
            # (правда, автор поста останется неизвестен)
            stat.log(
                0, f"WARNING: necroposters: comment {comment.id} for uninitalized post {comment.post_id}"
            )
            return

        try:
            user_rating = self._user_ratings[comment.author_id]
        except KeyError:
            stat.log(
                0, f"WARNING: necroposters: comment {comment.id} for unknown author id {comment.author_id}"
            )
            return

        days = int(tm - last_activity) // 3600 // 24
        score = days - self.min_inactivity_days + 1

        if score <= 0:
            # Не некропостер
            return

        if not self.authors_are_necroposters and self._post_authors.get(comment.post_id) == comment.author_id:
            # Некропостер, но в своём собственном посте, это можно
            return

        for nstat in self._stats:
            if nstat.min_rating is None or user_rating >= nstat.min_rating:
                nstat.add(comment.author_id, score)

    def stop(self, stat: TabunStat) -> None:
        for nstat in self._stats:
            suffix = f"_{nstat.min_rating:.2f}" if nstat.min_rating is not None else ""
            with (stat.destination / f"necroposters{suffix}.csv").open("w", encoding="utf-8") as fp:
                fp.write(utils.csvline("ID юзера", "Пользователь", "Число некропостов"))
                for user_id, count in sorted(nstat.count_by_user.items(), key=lambda x: x[1], reverse=True):
                    fp.write(
                        utils.csvline(
                            user_id,
                            stat.source.get_username_by_user_id(user_id),
                            count,
                        )
                    )

            with (stat.destination / f"necroposters{suffix}_score.csv").open("w", encoding="utf-8") as fp:
                fp.write(utils.csvline("ID юзера", "Пользователь", "Рейтинг некропостинга"))
                for user_id, score in sorted(nstat.score_by_user.items(), key=lambda x: x[1], reverse=True):
                    fp.write(
                        utils.csvline(
                            user_id,
                            stat.source.get_username_by_user_id(user_id),
                            score,
                        )
                    )

        super().stop(stat)
