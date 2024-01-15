import os
from typing import Optional, List, Dict, Tuple, Any, Set, Iterable
from datetime import date, datetime, timedelta

from tabun_stat import types, utils
from tabun_stat.stat import TabunStat
from tabun_stat.processors.base import BaseProcessor


class ActivityProcessor(BaseProcessor):
    def __init__(self, periods: Iterable[int] = (1, 7, 30), ratings: Iterable[Optional[float]] = (None, 0.0)) -> None:
        super().__init__()
        self.periods = tuple(periods)  # type: Tuple[int, ...]
        self._max_period = max(self.periods)  # type: int

        # activity — это список активности по дням. Каждый элемент — множество
        # айдишников пользователей, активных в этот день
        # users_with_posts — юзеры с постами
        # users_with_comments — юзеры с комментами

        self._ratings = {}  # type: Dict[Optional[float], Any]
        for rating in ratings:
            self._ratings[rating] = {
                'activity': [],
                'users_with_posts': set(),
                'users_with_comments': set(),
                'fp': None,
            }

        self._user_ratings = {}  # type: Dict[int, float]

        self._last_day = None  # type: Optional[date]

    def start(
        self, stat: TabunStat,
        min_date: Optional[datetime] = None, max_date: Optional[datetime] = None
    ) -> None:
        super().start(stat, min_date, max_date)
        assert self.stat

        header = ['Дата']
        for period in self.periods:
            if period == 1:
                header.append('Активны в этот день')
            else:
                header.append('Активны в последние {} дней'.format(period))

        for rating, item in self._ratings.items():
            filename = 'activity.csv'
            if rating is not None:
                filename = 'activity_{:.2f}.csv'.format(rating)
            item['fp'] = open(os.path.join(self.stat.destination, filename), 'w', encoding='utf-8')
            item['fp'].write(utils.csvline(*header))

    def process_user(self, user: types.User) -> None:
        # Собираем рейтинги пользователей
        self._user_ratings[user.id] = user.rating

    def process_post(self, post: types.Post) -> None:
        assert self.stat
        assert post.created_at_local is not None

        if post.author_id in self._user_ratings:
            rating = self._user_ratings[post.author_id]
        else:
            self.stat.log(0, 'WARNING: unknown author {} of post {}'.format(post.author_id, post.id))
            rating = 0.0

        self._put_activity(0, post.author_id, post.created_at_local, rating)

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat
        assert comment.created_at_local is not None

        if comment.author_id in self._user_ratings:
            rating = self._user_ratings[comment.author_id]
        else:
            self.stat.log(0, 'WARNING: unknown author {} of comment {}'.format(comment.author_id, comment.id))
            rating = 0.0

        self._put_activity(1, comment.author_id, comment.created_at_local, rating)

    def _put_activity(self, idx: int, user_id: int, created_at_local: datetime, rating: float) -> None:
        # idx: 0 - пост, 1 - коммент

        assert self.stat

        # Накатываем часовой пояс пользователя для определения местной границы суток
        day = created_at_local.date()

        if self._last_day is None:
            # Если это первый вызов _put_activity
            self._last_day = day
            for item in self._ratings.values():
                item['activity'].append((set(), set()))
                assert len(item['activity']) == 1

        else:
            assert day >= self._last_day  # TabunStat нам гарантирует это

            # Если день изменился, то сливаем всю прошлую статистику
            # в результат и добавляем следующий день на обработку
            while day > self._last_day:
                for item in self._ratings.values():
                    self._flush_activity(item)
                self._last_day += timedelta(days=1)
                # Удаляем лишние старые дни и добавляем новый день
                for item in self._ratings.values():
                    if self._max_period > 1:
                        item['activity'] = item['activity'][-(self._max_period - 1):] + [(set(), set())]
                    else:
                        item['activity'] = [(set(), set())]

        for item_rating, item in self._ratings.items():
            if item_rating is not None and rating < item_rating:
                continue
            item['activity'][-1][idx].add(user_id)

    def _flush_activity(self, item: Dict[str, Any]) -> None:
        stat = [str(self._last_day)]  # type: List[Any]

        for period in self.periods:
            # Собираем все id за последние period дней
            all_users = set()  # type: Set[int]

            for a, b in item['activity'][-period:]:
                all_users = all_users | a | b
                item['users_with_posts'] = item['users_with_posts'] | a
                item['users_with_comments'] = item['users_with_comments'] | b

            stat.append(len(all_users))

        # И пишем собранные числа в статистику
        assert item['fp']
        item['fp'].write(utils.csvline(*stat))

    def stop(self) -> None:
        assert self.stat

        for item in self._ratings.values():
            if self._last_day is not None:
                self._flush_activity(item)
            if item['fp']:
                item['fp'].close()
                item['fp'] = None

        for rating, item in self._ratings.items():
            filename = 'active_users.txt'
            if rating is not None:
                filename = 'active_users_{:.2f}.txt'.format(rating)

            if rating is None:
                users_all = len(self._user_ratings)
            else:
                users_all = len([x for x in self._user_ratings.values() if x >= rating])

            with open(os.path.join(self.stat.destination, filename), 'w', encoding='utf-8') as fp:
                fp.write('Всего юзеров: {}\n'.format(users_all))
                fp.write('Юзеров с постами: {}\n'.format(len(item['users_with_posts'])))
                fp.write('Юзеров с комментами: {}\n'.format(len(item['users_with_comments'])))
                fp.write('Юзеров с постами и комментами: {}\n'.format(len(item['users_with_posts'] & item['users_with_comments'])))
                fp.write('Юзеров с постами или комментами: {}\n'.format(len(item['users_with_posts'] | item['users_with_comments'])))
                fp.write('Юзеров без постов и без комментов: {}\n'.format(users_all - len(item['users_with_posts'] | item['users_with_comments'])))
                fp.write('Юзеров с постами, но без комментов: {}\n'.format(len(item['users_with_posts'] - item['users_with_comments'])))
                fp.write('Юзеров с комментами, но без постов: {}\n'.format(len(item['users_with_comments'] - item['users_with_posts'])))

        super().stop()
