import os
from typing import Dict, List

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor


class DicesProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self._dices = {}  # type: Dict[int, List[int]]

    def process_post(self, post: types.Post) -> None:
        if '<span class="dice">' not in post.body:
            return
        self._process(post.author_id, post.body)

    def process_comment(self, comment: types.Comment) -> None:
        if '<span class="dice">' not in comment.body:
            return
        self._process(comment.author_id, comment.body)

    def _process(self, author_id: int, body: str) -> None:
        if author_id not in self._dices:
            self._dices[author_id] = [0, 0]
        self._dices[author_id][0] += 1  # Число публикаций с дайсами
        self._dices[author_id][1] += body.count('<span class="dice">')  # Число дайсов в этих публикациях

    def stop(self) -> None:
        assert self.stat

        with open(os.path.join(self.stat.destination, 'dices.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline('ID юзера', 'Пользователь', 'Сколько публикаций с дайсами', 'Сколько раз брошены дайсы'))
            for user_id, (msgs_count, dices_count) in sorted(self._dices.items(), key=lambda x: x[1][0], reverse=True):
                fp.write(utils.csvline(
                    user_id,
                    self.stat.source.get_username_by_user_id(user_id),
                    msgs_count,
                    dices_count
                ))

        super().stop()
