from dataclasses import dataclass
from datetime import datetime

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor


@dataclass(slots=True)
class CharInfo:
    count: int
    first_seen_at: datetime


class CharsProcessor(BaseProcessor):
    special_names: dict[str, str] = {
        '"': "Кавычка",
        ",": "Запятая",
        " ": "Пробел",
        "\xa0": "Неразр. пробел",
        "\t": "Табуляция",
        "\n": "Перенос строки",
        "\r": "Возврат каретки",
        "\u00ad": "Мягкий перенос",
        "\u200b": "Пробел нулевой ширины",
        "\u200d": "Zero Width Joiner",
        "\u200e": "Left-To-Right Mark",
        "\u200f": "Right-To-Left Mark",
        "\u2028": "Line Separator",
        "\u202c": "Pop Directional Formatting",
        "\u202d": "Left-To-Right Override",
        "\u202e": "Right-To-Left Override",
        "\ufeff": "Unicode BOM",
    }
    special_eng = "AOECKPXMaoeckpxmBTHy"

    def __init__(self) -> None:
        super().__init__()
        self._chars: dict[str, CharInfo] = {}

    def process_post(self, post: types.Post) -> None:
        self._process(post.body, post.created_at)
        for tag in post.tags:
            self._process(tag, post.created_at)

    def process_comment(self, comment: types.Comment) -> None:
        self._process(comment.body, comment.created_at)

    def _process(self, body: str, tm: datetime) -> None:
        body = body.strip()

        for c in body:
            try:
                self._chars[c].count += 1
            except KeyError:
                self._chars[c] = CharInfo(count=1, first_seen_at=tm)

    def stop(self) -> None:
        assert self.stat
        with (self.stat.destination / "chars.csv").open("w", encoding="utf-8") as fp:
            fp.write(utils.csvline("Символ", "Сколько раз встретился", "Дата первого появления"))

            for c, info in sorted(
                self._chars.items(),
                key=lambda x: (-x[1].count, x[1].first_seen_at.timestamp()),
            ):
                if c in self.special_names:
                    c = self.special_names[c]
                elif c in self.special_eng:
                    c = c + " (англ.)"
                elif not c.strip():
                    c = repr(c)
                first_seen_at_str = info.first_seen_at.astimezone(self.stat.tz).strftime("%Y-%m-%d %H:%M:%S")
                fp.write(utils.csvline(c, info.count, first_seen_at_str))

        super().stop()
