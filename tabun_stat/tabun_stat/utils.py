import importlib
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import IO, Any, Iterable, TypeVar

T = TypeVar("T")


class ProgressDrawer:
    def __init__(
        self,
        target: int,
        *,
        w: int = 60,
        progress_chars: str | None = None,
        prefix: str = "",
        postfix: str = "",
        file: IO[str] | None = None,
        good_charset: bool | None = None,
    ):
        if file is None:
            file = sys.stderr

        if good_charset is None:
            if hasattr(file, "encoding"):
                good_charset = str(file.encoding or "").lower() in (
                    "utf-8",
                    "utf-16",
                    "utf-16le",
                    "utf-16be",
                    "utf-32",
                )

        if not progress_chars:
            if good_charset:
                progress_chars = " ▏▎▍▌▋▊▉█"
            else:
                progress_chars = " -#"

        self.target = target
        self.w = max(1, w)
        self.progress_chars = progress_chars
        self.prefix = prefix
        self.postfix = postfix
        self.file = file
        self.good_charset = good_charset
        self.can_flush = hasattr(file, "flush")
        self.lb = "▕" if good_charset else " ["
        self.rb = "▏" if good_charset else "] "

        self.current = -1
        self.last_redraw_at = 0.0
        self.min_redraw_interval = 0.04  # 25fps
        self.last_line = ""
        self._lastlen = 0

    def update(self, current: int, *, force: bool = False) -> str | None:
        if not force and current == self.current:
            return None
        self.current = current
        tm = time.monotonic()

        # Если update вызывается слишком часто, то лишних перерисовок не делаем
        if not force and current != self.target and tm - self.last_redraw_at < self.min_redraw_interval:
            return None

        # Процент, который нужно закрасить на полоске
        part = (current * 1.0 / self.target) if self.target > 0 else 0.0
        part = min(max(0.0, part), 1.0)

        # Полоска состоит из трёх частей
        # [#########-     ]
        # Решёточки — заполненные блоки, пробелы — пустые,
        # дефис — частично заполненный блок, позволяющий более точно
        # отобразить состояние задачи

        # Число заполненных блоков на полоске
        full_blocks = int(part * self.w)
        # Число пустых блоков (минус один частично заполненный)
        empty_blocks = self.w - full_blocks - 1
        # Процент частичного заполнения одного частично заполненного блока
        part_block_position = (part * self.w) - full_blocks
        # Выбираем номер символа для частично заполненного блока
        part_block_num = int(part_block_position * (len(self.progress_chars) - 1))

        # Собираем полоску
        line_arr = [self.prefix, self.lb]
        line_arr.append(self.progress_chars[-1] * full_blocks)
        if full_blocks != self.w:
            line_arr.append(self.progress_chars[part_block_num])
        if empty_blocks > 0:
            line_arr.append(self.progress_chars[0] * empty_blocks)
        line_arr.extend(
            (
                self.rb,
                f"{part * 100:.1f}% ".rjust(7),
                f"({current}) ",
                self.postfix,
            )
        )

        line = "".join(line_arr)
        if not force and line == self.last_line:
            return None

        # И печатаем
        self._lastlen = self.fprint_substring(line, self._lastlen)
        self.last_line = line
        self.current = current
        self.last_redraw_at = tm
        return line

    def add_progress(self, value: int, *, force: bool = False) -> str | None:
        return self.update(self.current + value, force=force)

    def fprint_substring(self, s: str, l: int = 0) -> int:
        return fprint_substring(s, l=l, file=self.file, flush=self.can_flush)

    def set_target(self, target: int, *, update: bool = True) -> None:
        self.target = int(target)
        if update:
            self.update(self.current, force=True)


def fprint_substring(s: str, l: int = 0, file: IO[str] | None = None, flush: bool | None = None) -> int:
    """Печатает строку, затирая последние l символов. Возвращает длину печатаемой строки."""

    if file is None:
        file = sys.stderr
    if flush is None:
        flush = hasattr(file, "flush")

    x = []
    if l > 0:
        x.append("\b" * l)

    x.append(s)

    if len(s) < l:
        x.append(" " * (l - len(s)))
        x.append("\b" * (l - len(s)))

    file.write("".join(x))
    if flush:
        file.flush()
    return len(s)


def format_timedelta(tm: int | float | timedelta) -> str:
    if isinstance(tm, timedelta):
        tm = tm.total_seconds()
    tm = int(tm)

    minus = False
    if tm < 0:
        minus = True
        tm = -tm

    s = f"{tm % 60:02d}s"
    if tm >= 60:
        s = f"{(tm // 60) % 60:02d}m{s}"
    if tm >= 3600:
        s = f"{tm // 3600}h{s}"

    if minus:
        s = f"-{s}"
    return s


def import_string(s: str) -> object:
    if "." not in s:
        raise ValueError("import_string can import only objects using dot")

    module_name, attr = s.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def csvline(
    *args: object,
    end: str = "\n",
    delimiter: str = ",",
    quote: str = '"',
    always_quote: bool = False,
    slash_escape: bool = False,
) -> str:
    """Возвращает строку, пригодную для записи в csv-файл.

    :param args: объекты для записи (будут приведены к строке)
    :param end: что дописать в конец строки (по умолчанию перевод строки)
    :param delimeter: разделитель объектов (по умолчанию запятая)
    :param quote: кавычка, используемая для экранирования
    :param always_quote: оборачивать все объекты в кавычки, даже если
      нет необходимости
    :param slash_escape: экранировать кавычку слэшем, а не самой кавычкой
    """

    result: list[str] = []

    for x in args:
        if result:
            result.append(delimiter)
        x = str(x)

        if always_quote or quote in x or "\n" in x:
            if slash_escape:
                x = x.replace(quote, "\\" + quote)
            else:
                x = x.replace(quote, quote + quote)
            x = quote + x + quote

        result.append(x)

    result.append(end)

    return "".join(result)


def force_utc(tm: datetime) -> datetime:
    if tm.tzinfo is None:
        raise ValueError("datetime object must be aware")
    return tm.astimezone(timezone.utc)


def filter_split(f: str) -> tuple[str, str]:
    """Разделяет фильтр на название поля и операцию."""
    if "__" in f:
        return tuple(f.split("__", 1))  # type: ignore
    raise ValueError(f"Invalid filter: {f!r}")


def filter_act(act: str, left: Any, right: Any) -> bool:
    """Применяет операцию (lt/lte/gt/gte) к указанным значениям."""
    if act == "lt":
        return bool(left < right)
    if act == "lte":
        return bool(left <= right)
    if act == "gt":
        return bool(left > right)
    if act == "gte":
        return bool(left >= right)
    raise ValueError(f"Invalid act: {act!r}")


def drop_duplicates(items: Iterable[T]) -> list[T]:
    result: list[T] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
