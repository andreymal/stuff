import math
import os
from typing import Iterable

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor


class UsersRatingsProcessor(BaseProcessor):
    def __init__(self, steps: Iterable[int] = (10, 100)):
        super().__init__()

        self._ratings: dict[int, dict[int, int]] = {}
        self._zero = 0  # Число пользователей с ровно нулевым рейтингом
        for step in steps:
            self._ratings[step] = {}

    def process_user(self, user: types.User) -> None:
        for step in self._ratings:
            step_vote = int(math.floor(user.rating / step) * step)
            if step_vote not in self._ratings[step]:
                self._ratings[step][step_vote] = 0
            self._ratings[step][step_vote] += 1

        if user.rating == 0.0:
            self._zero += 1

    def end_users(self, stat: types.UsersLimits) -> None:
        assert self.stat

        for step in self._ratings:
            with open(
                os.path.join(self.stat.destination, f"users_ratings_{step}.csv"),
                "w",
                encoding="utf-8",
            ) as fp:
                fp.write(utils.csvline("Рейтинг", "Число пользователей"))

                step_vote = min(self._ratings[step])
                vmax = max(self._ratings[step])

                while step_vote <= vmax:
                    count = self._ratings[step].get(step_vote, 0)

                    step_vote_end = round(step_vote + (step - 0.01), 2)
                    fp.write(utils.csvline(f"{step_vote:.2f} – {step_vote_end:.2f}", count))

                    step_vote += step

        with open(os.path.join(self.stat.destination, "users_ratings_zero.txt"), "w", encoding="utf-8") as fp:
            fp.write(f"{self._zero}\n")
