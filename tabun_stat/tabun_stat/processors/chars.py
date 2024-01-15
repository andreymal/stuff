import os
from typing import Dict, List
from datetime import datetime
from collections import Counter

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor


class CharsProcessor(BaseProcessor):
    def __init__(self) -> None:
        super().__init__()
        self._chars = {}  # type: Dict[str, List[int]]

    def process_post(self, post: types.Post) -> None:
        self._process(post.body, post.created_at)

    def process_comment(self, comment: types.Comment) -> None:
        self._process(comment.body, comment.created_at)

    def _process(self, body: str, tm: datetime) -> None:
        body = body.strip()

        counter = Counter(body)
        for c, cnt in counter.items():
            try:
                self._chars[c][0] += cnt
            except KeyError:
                self._chars[c] = [cnt, int((tm - datetime(1970, 1, 1, 0, 0, 0)).total_seconds())]

    def stop(self) -> None:
        assert self.stat
        with open(os.path.join(self.stat.destination, 'chars.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline('Символ', 'Сколько раз встретился'))

            for c, x in sorted(self._chars.items(), key=lambda x: [-x[1][0], x[1][1]]):
                cnt, created_at_unix = x

                # created_at = utils.apply_tzinfo(
                #     datetime.utcfromtimestamp(created_at_unix),
                #     self.stat.timezone
                # )

                if c == '"':
                    c = 'Кавычка'
                elif c == ',':
                    c = 'Запятая'
                elif c == ' ':
                    c = 'Пробел'
                elif c == '\u00a0':
                    c = 'Неразр. пробел'
                elif c == '\t':
                    c = 'Табуляция'
                elif c == '\n':
                    c = 'Перенос строки'
                elif c == '\r':
                    c = 'Возврат каретки'
                elif c.lower() in ('a', 'o', 'e', 'c', 'k', 'p', 'x', 'm') or c in ('B', 'T', 'H', 'y'):
                    c = c + ' (англ.)'
                elif not c.strip():
                    c = repr(c)
                fp.write(utils.csvline(c, cnt))

        super().stop()
