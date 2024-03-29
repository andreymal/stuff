from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


class PostsRatingsProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()

        # {год: {рейтинг: кол-во}}
        self._stat: dict[int, dict[int, int]] = {}

    def process_post(self, stat: TabunStat, post: types.Post) -> None:
        assert post.created_at_local is not None

        vote = post.vote_value
        if vote is None or not post.body:
            return  # Не забываем, что рейтинг поста может быть неизвестен

        # Забираем год в правильном часовом поясе
        year = post.created_at_local.year

        if year not in self._stat:
            self._stat[year] = {}
        if vote not in self._stat[year]:
            self._stat[year][vote] = 0
        self._stat[year][vote] += 1

    def stop(self, stat: TabunStat) -> None:
        min_rating = 0
        max_rating = 0
        for votes_dict in self._stat.values():
            min_rating = min(min(votes_dict), min_rating)
            max_rating = max(max(votes_dict), max_rating)

        header = ["Рейтинг", "За всё время"]
        for year in sorted(self._stat):
            header.append(f"{year} год")

        with (stat.destination / "posts_ratings.csv").open("w", encoding="utf-8") as fp:
            fp.write(utils.csvline(*header))
            for vote in range(min_rating, max_rating + 1):
                line = [vote, 0]
                for year in sorted(self._stat):
                    line.append(self._stat[year].get(vote, 0))
                    line[1] += line[-1]
                fp.write(utils.csvline(*line))

        super().stop(stat)
