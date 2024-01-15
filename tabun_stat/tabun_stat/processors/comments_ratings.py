import os
from typing import Dict

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor


class CommentsRatingsProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self._stat = {}  # type: Dict[int, Dict[int, int]]

    def process_comment(self, comment: types.Comment) -> None:
        assert self.stat
        assert comment.created_at_local is not None

        vote = comment.vote_value

        # Забираем год в правильном часовом поясе
        year = comment.created_at_local.year

        if year not in self._stat:
            self._stat[year] = {}
        if vote not in self._stat[year]:
            self._stat[year][vote] = 0
        self._stat[year][vote] += 1

    def stop(self) -> None:
        assert self.stat

        min_rating = 0
        max_rating = 0
        for votes_dict in self._stat.values():
            min_rating = min(min(votes_dict), min_rating)
            max_rating = max(max(votes_dict), max_rating)

        header = ['Рейтинг', 'За всё время']
        for year in sorted(self._stat):
            header.append('{} год'.format(year))

        with open(os.path.join(self.stat.destination, 'comments_ratings.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline(*header))
            for vote in range(min_rating, max_rating + 1):
                line = [vote, 0]
                for year in sorted(self._stat):
                    line.append(self._stat[year].get(vote, 0))
                    line[1] += line[-1]
                fp.write(utils.csvline(*line))

        super().stop()
