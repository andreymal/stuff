import os
import sys
import time
from datetime import datetime, timedelta
from itertools import chain
from typing import Any, Callable, Iterator

import pytz

from tabun_stat import types, utils
from tabun_stat.datasource.base import BaseDataSource
from tabun_stat.processors.base import BaseProcessor


class TabunStat:
    timezone: pytz.BaseTzInfo

    def __init__(
        self,
        source: BaseDataSource,
        destination: str,
        verbosity: int = 0,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
        timezone: str | pytz.BaseTzInfo | None = None,
    ):
        """
        :param BaseDataSource source: источник данных для обработки
        :param str destination: каталог, в который будет складываться готовая
          статистика
        :param int verbosity: уровень подробности логов (0 без логов,
          1 базовые логи, 2 с прогресс-барами)
        :param datetime min_date: минимальная дата обрабатываемых постов
          и комментов
        :param datetime max_date: максимальная дата обрабатываемых постов
          и комментов (если не указана, то по умолчанию используется момент
          вызова метода go)
        :param timezone: часовой пояс для обработки дат, используется
          некоторыми обработчиками (BaseTzInfo или строка, по умолчанию UTC)
        """

        self.source = source
        self.destination = os.path.abspath(destination)
        self.min_date = utils.force_utc(min_date).replace(tzinfo=None) if min_date else None
        self.max_date = utils.force_utc(max_date).replace(tzinfo=None) if max_date else None
        self.verbosity = verbosity

        # Парсим часовой пояс
        if isinstance(timezone, str):
            self.timezone = pytz.timezone(timezone)
        elif not timezone:
            self.timezone = pytz.timezone("UTC")
        else:
            self.timezone = timezone

        # Проверяем адекватность дат
        if self.min_date and self.max_date and self.max_date < self.min_date:
            raise ValueError("min_date is less than max_date")

        if os.path.exists(self.destination) and os.listdir(self.destination):
            raise OSError(f"Directory {str(self.destination)!r} is not empty")

        self.log: Callable[..., Any] = self._default_log
        self._isatty: bool | None = None

        self._processors: list[BaseProcessor] = []
        self._perf: list[float] = []
        self._source_perf = 0.0

    def _default_log(self, verbosity: int, *args: Any, end: str = "\n", for_tty: bool = False) -> None:
        if verbosity > self.verbosity:
            return
        if not args or args == ("",):
            return
        if for_tty:
            if self._isatty is None:
                self._isatty = sys.stderr.isatty()
            if not self._isatty:
                return

        print(*args, file=sys.stderr, end=end, flush=True)

    def _empty_log(self, verbosity: int, *args: Any, end: str = "\n", for_tty: bool = False) -> None:
        pass

    def set_log_function(self, func: Callable[..., None]) -> None:
        """Устанавливает функцию, печатающую лог. Должна принимать verbosity,
        *args, end и for_tty. По умолчанию всё печатается в stderr.
        """
        if func is None:
            func = self._empty_log
        self.log = func

    def add_processor(self, processor: BaseProcessor) -> bool:
        """Добавляет обработчик данных."""
        if processor not in self._processors:
            self._processors.append(processor)
            return True
        return False

    def remove_processor(self, processor: BaseProcessor) -> bool:
        """Удаляет обработчик данных."""
        if processor in self._processors:
            self._processors.remove(processor)
            return True
        return False

    def remove_all_processors(self) -> bool:
        if not self._processors:
            return False
        self._processors.clear()
        return True

    def destroy(self) -> None:
        """Прибирает оперативку."""
        self._processors = []
        self.source = None  # type: ignore

    # Замерялка производительности

    def _perfmon_reset(self) -> None:
        self._perf = [0.0] * len(self._processors)
        self._source_perf = 0.0

    def _perfmon_put(self, idx: int, duration: float) -> None:
        self._perf[idx] += duration

    def _print_perf_info(self, full_duration: float | None = None) -> None:
        source_dur_str = f"{self._source_perf:.2f}"
        rjust = len(source_dur_str)

        etc_dur_str: str | None = None
        if full_duration is not None:
            etc_duration = full_duration - sum(self._perf) - self._source_perf
            etc_dur_str = f"{etc_duration:.2f}"

        if etc_dur_str and len(etc_dur_str) > rjust:
            rjust = len(etc_dur_str)

        for duration, p in sorted(zip(self._perf, self._processors), key=lambda x: x[0], reverse=True):
            dur_str = f"{duration:.2f}"
            if len(dur_str) > rjust:
                rjust = len(dur_str)
            else:
                dur_str = dur_str.rjust(rjust)
            pname = type(p).__name__
            self.log(1, f"{dur_str}s {pname}")

        source_dur_str = source_dur_str.rjust(rjust)
        self.log(1, f"{source_dur_str}s source queries")
        if etc_dur_str is not None:
            etc_dur_str = etc_dur_str.rjust(rjust)
            self.log(1, f"{etc_dur_str}s other")

    # Но сверху это всё вспомогательная вода, самая мякотка тут ↓

    def go(self) -> None:
        """Запускает подсчёт статистики. Суть такова:

        * если max_date не указан, то ставит текущее время;
        * создаёт каталог destination;
        * вызывает метод start у обработчиков, передавая им себя, min_date
          и max_date;
        * по очереди отдаёт обработку юзеров, блогов, постов и комментов,
          причём для постов и комментов гарантируется хронологический порядок;
        * после всего этого вызывает stop у обработчиков.
        """

        # Фиксируем максимальную дату, чтобы уменьшить всякую неконсистентность в статистике
        started_at = datetime.utcnow()
        started_at_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
        self.log(1, f"tabun_stat started at {started_at_str} UTC")
        self._perfmon_reset()

        started_at_unix = time.time()

        # Определяемся с охватываемым периодом времени. Если максимальная дата
        # не указано, то явно прописываем текущую дату для большей
        # консистентности статистики (чтобы новые посты и комменты, появившиеся
        # уже во время подсчёта статистики, не испортили тут всё)
        min_date = self.min_date
        max_date = self.max_date
        if not max_date and (not min_date or started_at > min_date):
            max_date = started_at

        # Уведомляем о периоде пользователя
        self.log(
            1,
            "Date interval for posts and comments (UTC): [{} .. {})".format(
                min_date.strftime("%Y-%m-%d %H:%M:%S") if min_date else "-inf",
                max_date.strftime("%Y-%m-%d %H:%M:%S") if max_date else "+inf",
            ),
        )

        # Составляем фильтр для источника
        # (сама максимальная дата в правый край диапазона не входит)
        datefilters = {"created_at__lt": max_date}
        if min_date:
            datefilters["created_at__gte"] = min_date

        # Создаём каталог, в который будет сгружена статистика
        if not os.path.isdir(self.destination):
            os.makedirs(self.destination)
        elif os.listdir(self.destination):
            raise OSError(f"Directory {str(self.destination)!r} is not empty")

        # И дальше просто обрабатываем по очереди
        finished_at: datetime | None = None

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.start(self, min_date, max_date)
            self._perfmon_put(idx, time.time() - tm)

        try:
            self._process_users(datefilters)
            self._process_blogs(datefilters)
            self._process_posts_and_comments(datefilters)

            finished_at = datetime.utcnow()

        except (KeyboardInterrupt, SystemExit):
            self.log(1, "\nInterrupted")

        finally:
            self.log(1, "Finishing:", end="           ")
            drawer = utils.progress_drawer(target=len(self._processors), show_count=True, use_unicode=True)
            self.log(2, drawer.send(None) or "", end="", for_tty=True)

            for idx, p in enumerate(self._processors):
                self.log(2, drawer.send(idx + 1) or "", end="", for_tty=True)
                tm = time.time()
                p.stop()
                self._perfmon_put(idx, time.time() - tm)

            try:
                drawer.send(None)
            except StopIteration:
                pass
            self.log(1, "| Done.")

        if finished_at is not None:
            finished_at_unix = time.time()
            duration = finished_at_unix - started_at_unix
            self.log(
                1,
                "tabun_stat finished at {} UTC ({})".format(
                    finished_at.strftime("%Y-%m-%d %H:%M:%S"),
                    utils.format_timedelta(duration),
                ),
            )

            if self.verbosity >= 1:
                self.log(1, "\nPerformance info:")
                self._print_perf_info(duration)

    def _process_users(self, datefilters: dict[str, Any]) -> None:
        self.log(1, "Processing users:", end="    ")

        all_tm = time.time()
        tm = all_tm
        stat = self.source.get_users_limits()
        self._source_perf += time.time() - tm

        if not stat.count:
            self.log(1, "nothing to do.")
            return

        drawer = utils.progress_drawer(target=stat.count, show_count=True, use_unicode=True)
        self.log(2, drawer.send(None) or "", end="", for_tty=True)

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.begin_users(stat)
            self._perfmon_put(idx, time.time() - tm)

        i = 0
        tm = time.time()
        for users in self.source.iter_users():  # никакая сортировка не гарантируется
            self._source_perf += time.time() - tm
            for user in users:
                user.registered_at_local = utils.apply_tzinfo(user.registered_at, self.timezone)

            i += len(users)
            self.log(2, drawer.send(i) or "", end="", for_tty=True)

            for idx, p in enumerate(self._processors):
                tm = time.time()
                for user in users:
                    p.process_user(user)
                self._perfmon_put(idx, time.time() - tm)

            tm = time.time()

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.end_users(stat)
            self._perfmon_put(idx, time.time() - tm)

        try:
            drawer.send(None)
        except StopIteration:
            pass

        self.log(1, f"| Done in {utils.format_timedelta(time.time() - all_tm)}.")

    def _process_blogs(self, datefilters: dict[str, Any]) -> None:
        self.log(1, "Processing blogs:", end="    ")

        all_tm = time.time()
        tm = all_tm
        stat = self.source.get_blogs_limits()
        self._source_perf += time.time() - tm

        if not stat.count:
            self.log(1, "nothing to do.")
            return
        assert stat.first_id is not None and stat.last_id is not None

        drawer = utils.progress_drawer(target=stat.count, show_count=True, use_unicode=True)
        self.log(2, drawer.send(None) or "", end="", for_tty=True)

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.begin_blogs(stat)
            self._perfmon_put(idx, time.time() - tm)

        i = 0
        tm = time.time()
        for blogs in self.source.iter_blogs():  # никакая сортировка не гарантируется
            self._source_perf += time.time() - tm
            for blog in blogs:
                blog.created_at_local = utils.apply_tzinfo(blog.created_at, self.timezone)

            i += len(blogs)
            self.log(2, drawer.send(i) or "", end="", for_tty=True)
            for idx, p in enumerate(self._processors):
                tm = time.time()
                for blog in blogs:
                    p.process_blog(blog)
                self._perfmon_put(idx, time.time() - tm)

            tm = time.time()

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.end_blogs(stat)
            self._perfmon_put(idx, time.time() - tm)

        try:
            drawer.send(None)
        except StopIteration:
            pass

        self.log(1, f"| Done in {utils.format_timedelta(time.time() - all_tm)}.")

    def _process_posts_and_comments(self, datefilters: dict[str, Any]) -> None:
        self.log(1, "Processing messages:", end=" ")

        l = "(fetch stat...)"
        self.log(1, l, end="", for_tty=True)

        all_tm = time.time()
        tm = all_tm
        stat_posts = self.source.get_posts_limits(filters=datefilters)
        stat_comments = self.source.get_comments_limits(filters=datefilters)
        self._source_perf += time.time() - tm

        self.log(1, "\b" * len(l), end="", for_tty=True)
        del l

        # Если нет ни постов, ни комментов, то делать нечего
        if (
            stat_posts.first_created_at is None or stat_posts.last_created_at is None or not stat_posts.count
        ) and (
            stat_comments.first_created_at is None
            or stat_comments.last_created_at is None
            or not stat_comments.count
        ):
            self.log(1, "nothing to do.")
            return

        drawer = utils.progress_drawer(
            target=stat_posts.count + stat_comments.count, show_count=True, use_unicode=True
        )
        self.log(2, drawer.send(None) or "", end="", for_tty=True)

        # Высчитываем охватываемый интервал времени
        if stat_posts.first_created_at and stat_comments.first_created_at:
            min_date = min(stat_posts.first_created_at, stat_comments.first_created_at)
        else:
            d = stat_posts.first_created_at or stat_comments.first_created_at
            assert d is not None
            min_date = d

        if stat_posts.last_created_at and stat_comments.last_created_at:
            max_date = max(stat_posts.last_created_at, stat_comments.last_created_at)
        else:
            d = stat_posts.last_created_at or stat_comments.last_created_at
            assert d is not None
            max_date = d

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.begin_messages(stat_posts, stat_comments)
            self._perfmon_put(idx, time.time() - tm)

        # И дальше забираем посты и комменты по дням, сортируя их строго по времени
        i = 0
        for source_perf, posts, comments in iter_messages(min_date, max_date, self.source):
            self._source_perf += source_perf

            messages: list[types.Post | types.Comment] = []
            messages.extend(posts)
            messages.extend(comments)

            if messages:
                messages.sort(key=lambda x: x.created_at)

            for message in messages:
                message.created_at_local = utils.apply_tzinfo(message.created_at, self.timezone)

            for idx, p in enumerate(self._processors):
                tm = time.time()
                for message in messages:
                    if isinstance(message, types.Comment):
                        p.process_comment(message)
                    else:
                        p.process_post(message)
                self._perfmon_put(idx, time.time() - tm)

            i += len(messages)
            self.log(2, drawer.send(i) or "", end="", for_tty=True)

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.end_messages(stat_posts, stat_comments)
            self._perfmon_put(idx, time.time() - tm)

        try:
            drawer.send(None)
        except StopIteration:
            pass

        self.log(1, f"| Done in {utils.format_timedelta(time.time() - all_tm)}.")


def iter_messages(
    min_date: datetime,
    max_date: datetime,
    source: BaseDataSource,
) -> Iterator[tuple[float, list[types.Post], list[types.Comment]]]:
    day = min_date
    while True:
        next_day = day + timedelta(days=1)
        assert not next_day.tzinfo

        filters = {"created_at__gte": day}
        if next_day >= max_date:
            filters["created_at__lte"] = max_date
        else:
            filters["created_at__lt"] = next_day

        tm = time.time()
        posts = list(chain.from_iterable(source.iter_posts(filters=filters)))
        comments = list(chain.from_iterable(source.iter_comments(filters=filters)))
        source_perf = time.time() - tm

        yield source_perf, posts, comments

        if next_day >= max_date:
            break
        day = next_day
