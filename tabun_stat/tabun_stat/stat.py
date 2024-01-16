import sys
import time
from datetime import datetime, timedelta, timezone, tzinfo
from itertools import chain
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Iterator, Protocol
from zoneinfo import ZoneInfo

from tabun_stat import types, utils
from tabun_stat.datasource.base import BaseDataSource
from tabun_stat.processors.base import BaseProcessor


class LogCallable(Protocol):
    def __call__(
        self,
        verbosity: int,
        *args: object,
        end: str = "\n",
        for_tty: bool = False,
    ) -> None:
        ...


class TabunStat:
    def __init__(
        self,
        *,
        source: BaseDataSource,
        destination: str | Path,
        verbosity: int = 0,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
        tz: str | tzinfo | None = None,
    ):
        """
        :param source: источник данных для обработки
        :param destination: каталог, в который будет складываться готовая
          статистика
        :param verbosity: уровень подробности логов (0 без логов,
          1 базовые логи, 2 с прогресс-барами)
        :param min_date: минимальная дата обрабатываемых постов и комментов
        :param max_date: максимальная дата обрабатываемых постов и комментов
          (если не указана, то по умолчанию используется момент вызова метода
          go)
        :param tz: часовой пояс для обработки дат, используется
          некоторыми обработчиками (ZoneInfo или строка, по умолчанию UTC)
        """

        self.source = source
        self.destination = Path(destination).resolve()
        self.min_date = utils.force_utc(min_date) if min_date is not None else None
        self.max_date = utils.force_utc(max_date) if max_date is not None else None
        self.verbosity = verbosity

        # Парсим часовой пояс
        if tz is None:
            tz = timezone.utc
        elif isinstance(tz, str):
            tz = ZoneInfo(tz)
        self.tz = tz

        # Проверяем адекватность дат
        if self.min_date is not None and self.max_date is not None and self.max_date < self.min_date:
            raise ValueError("max_date is earlier than min_date")

        self.log: LogCallable = self._default_log
        self._isatty: bool | None = None

        self._processors: list[BaseProcessor] = []
        self._perf: list[float] = []
        self._source_perf = 0.0
        self._source_perf_threaded = 0.0

    def _default_log(self, verbosity: int, *args: object, end: str = "\n", for_tty: bool = False) -> None:
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

    def _empty_log(self, verbosity: int, *args: object, end: str = "\n", for_tty: bool = False) -> None:
        pass

    def set_log_function(self, func: LogCallable) -> None:
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
        self._processors.clear()

    # Замерялка производительности

    def _perfmon_reset(self) -> None:
        self._perf = [0.0] * len(self._processors)
        self._source_perf = 0.0
        self._source_perf_threaded = 0.0

    def _perfmon_put(self, idx: int, duration: float) -> None:
        self._perf[idx] += duration

    def _generate_perf_info(self, full_duration: float | None = None) -> Iterator[str]:
        source_dur_str = f"{self._source_perf:.2f}"
        source_dur_thr_str = f"{self._source_perf_threaded:.2f}"
        rjust = max(len(source_dur_str), len(source_dur_thr_str))

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
            yield f"{dur_str}s {pname}"

        source_dur_str = source_dur_str.rjust(rjust)
        source_dur_thr_str = source_dur_thr_str.rjust(rjust)
        yield f"{source_dur_str}s source queries"
        yield f"{source_dur_thr_str}s source queries (in a separate thread)"

        if etc_dur_str is not None:
            etc_dur_str = etc_dur_str.rjust(rjust)
            yield f"{etc_dur_str}s other"

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

        started_at = datetime.now(timezone.utc)
        started_at_str = started_at.strftime("%Y-%m-%d %H:%M:%S")
        self.log(1, f"tabun_stat started at {started_at_str} UTC")
        self._perfmon_reset()

        started_at_mono = time.monotonic()

        # Определяемся с охватываемым периодом времени. Если максимальная дата
        # не указана, то явно прописываем текущую дату для большей
        # консистентности статистики (чтобы новые посты и комменты, появившиеся
        # уже во время подсчёта статистики, не испортили тут всё)
        min_date = self.min_date
        max_date = self.max_date
        if max_date is None and (min_date is None or started_at > min_date):
            max_date = started_at

        # Уведомляем пользователя об охватываемом периоде
        self.log(
            1,
            "Date interval for posts and comments (UTC): [{} .. {})".format(
                min_date.strftime("%Y-%m-%d %H:%M:%S") if min_date is not None else "-inf",
                max_date.strftime("%Y-%m-%d %H:%M:%S") if max_date is not None else "+inf",
            ),
        )

        # Создаём каталог, в который будет сгружена статистика
        if self.destination.exists():
            if any(self.destination.iterdir()):
                raise OSError(f"Directory {str(self.destination)!r} is not empty")
        else:
            self.destination.mkdir(parents=True, exist_ok=True)

        # Подключаемся к источнику данных
        tm = time.monotonic()
        self.source.start(self)
        self._source_perf += time.monotonic() - tm

        # И дальше просто обрабатываем по очереди
        finished_at: datetime | None = None

        for idx, p in enumerate(self._processors):
            tm = time.monotonic()
            p.start(self, min_date, max_date)
            self._perfmon_put(idx, time.monotonic() - tm)

        try:
            self._process_users(max_date)
            self._process_blogs()
            self._process_posts_and_comments(min_date, max_date)

            finished_at = datetime.now(timezone.utc)

        except (KeyboardInterrupt, SystemExit):
            self.log(1, "\nInterrupted")

        finally:
            self.log(1, "Finishing:", end="           ")
            drawer = utils.ProgressDrawer(len(self._processors)) if self.verbosity >= 2 else None
            if drawer is not None:
                drawer.update(0)

            for idx, p in enumerate(self._processors):
                if drawer is not None:
                    drawer.add_progress(1)
                tm = time.monotonic()
                p.stop()
                self._perfmon_put(idx, time.monotonic() - tm)

            if drawer is not None:
                drawer.add_progress(0, force=True)
            self.log(1, "| Done.")

        if finished_at is not None:
            finished_at_mono = time.monotonic()
            duration = finished_at_mono - started_at_mono
            self.log(
                1,
                "tabun_stat finished at {} UTC ({})".format(
                    finished_at.strftime("%Y-%m-%d %H:%M:%S"),
                    utils.format_timedelta(duration),
                ),
            )

            if self.verbosity >= 1:
                self.log(1, "\nPerformance info:")
                for x in self._generate_perf_info(duration):
                    self.log(1, x)

    def _process_users(self, max_date: datetime | None) -> None:
        self.log(1, "Processing users:", end="    ")

        datefilters = {}
        # min_date не учитываем специально
        if max_date is not None:
            datefilters["registered_at__lt"] = max_date

        all_tm = time.monotonic()
        tm = all_tm
        stat = self.source.get_users_limits(datefilters)
        self._source_perf += time.monotonic() - tm

        if not stat.count:
            self.log(1, "nothing to do.")
            return

        drawer = utils.ProgressDrawer(target=stat.count) if self.verbosity >= 2 else None
        if drawer is not None:
            drawer.update(0)

        for idx, p in enumerate(self._processors):
            tm = time.monotonic()
            p.begin_users(stat)
            self._perfmon_put(idx, time.monotonic() - tm)

        tm = time.monotonic()
        for users in self.source.iter_users(datefilters):  # никакая сортировка не гарантируется
            self._source_perf += time.monotonic() - tm
            for user in users:
                if user.registered_at.tzinfo is None:
                    raise ValueError("User.registered_at must be aware datetime")
                user.registered_at_local = user.registered_at.astimezone(self.tz)

            if drawer is not None:
                drawer.add_progress(len(users))

            for idx, p in enumerate(self._processors):
                tm = time.monotonic()
                for user in users:
                    p.process_user(user)
                self._perfmon_put(idx, time.monotonic() - tm)

            tm = time.monotonic()

        for idx, p in enumerate(self._processors):
            tm = time.monotonic()
            p.end_users(stat)
            self._perfmon_put(idx, time.monotonic() - tm)

        if drawer is not None:
            drawer.add_progress(0, force=True)

        self.log(1, f"| Done in {utils.format_timedelta(time.monotonic() - all_tm)}.")

    def _process_blogs(self) -> None:
        self.log(1, "Processing blogs:", end="    ")

        all_tm = time.monotonic()
        tm = all_tm
        stat = self.source.get_blogs_limits()
        self._source_perf += time.monotonic() - tm

        if not stat.count:
            self.log(1, "nothing to do.")
            return
        assert stat.first_id is not None and stat.last_id is not None

        drawer = utils.ProgressDrawer(target=stat.count) if self.verbosity >= 2 else None
        if drawer is not None:
            drawer.update(0)

        for idx, p in enumerate(self._processors):
            tm = time.monotonic()
            p.begin_blogs(stat)
            self._perfmon_put(idx, time.monotonic() - tm)

        tm = time.monotonic()
        for blogs in self.source.iter_blogs():  # никакая сортировка не гарантируется
            self._source_perf += time.monotonic() - tm
            for blog in blogs:
                if blog.created_at.tzinfo is None:
                    raise ValueError("Blog.created_at must be aware datetime")
                blog.created_at_local = blog.created_at.astimezone(self.tz)

            if drawer is not None:
                drawer.add_progress(len(blogs))

            for idx, p in enumerate(self._processors):
                tm = time.monotonic()
                for blog in blogs:
                    p.process_blog(blog)
                self._perfmon_put(idx, time.monotonic() - tm)

            tm = time.monotonic()

        for idx, p in enumerate(self._processors):
            tm = time.monotonic()
            p.end_blogs(stat)
            self._perfmon_put(idx, time.monotonic() - tm)

        if drawer is not None:
            drawer.add_progress(0, force=True)

        self.log(1, f"| Done in {utils.format_timedelta(time.monotonic() - all_tm)}.")

    def _process_posts_and_comments(self, min_date: datetime | None, max_date: datetime | None) -> None:
        self.log(1, "Processing messages:", end=" ")

        datefilters = {}
        if min_date is not None:
            datefilters["created_at__gte"] = min_date
        if max_date is not None:
            datefilters["created_at__lt"] = max_date

        l = "(fetch stat...)"
        self.log(1, l, end="", for_tty=True)

        all_tm = time.monotonic()
        tm = all_tm
        stat_posts = self.source.get_posts_limits(filters=datefilters)
        stat_comments = self.source.get_comments_limits(filters=datefilters)
        self._source_perf += time.monotonic() - tm

        self.log(1, "\b" * len(l), end="", for_tty=True)
        del l

        # Если нет ни постов, ни комментов, то делать нечего
        no_posts = (
            stat_posts.first_created_at is None or stat_posts.last_created_at is None or not stat_posts.count
        )
        no_comments = (
            stat_comments.first_created_at is None
            or stat_comments.last_created_at is None
            or not stat_comments.count
        )
        if no_posts and no_comments:
            self.log(1, "nothing to do.")
            return

        for k in ("first_created_at", "last_created_at"):
            if getattr(stat_posts, k).tzinfo is None:
                raise ValueError(f"PostsLimits.{k} must be aware datetime")
            if getattr(stat_comments, k).tzinfo is None:
                raise ValueError(f"CommentsLimits.{k} must be aware datetime")

        drawer = (
            utils.ProgressDrawer(target=stat_posts.count + stat_comments.count)
            if self.verbosity >= 2
            else None
        )
        if drawer is not None:
            drawer.update(0)

        # Высчитываем охватываемый интервал времени
        if stat_posts.first_created_at and stat_comments.first_created_at:
            min_date = min(stat_posts.first_created_at, stat_comments.first_created_at)
        else:
            min_date = stat_posts.first_created_at or stat_comments.first_created_at

        if stat_posts.last_created_at and stat_comments.last_created_at:
            max_date = max(stat_posts.last_created_at, stat_comments.last_created_at)
        else:
            max_date = stat_posts.last_created_at or stat_comments.last_created_at

        assert min_date is not None
        assert max_date is not None

        for idx, p in enumerate(self._processors):
            tm = time.monotonic()
            p.begin_messages(stat_posts, stat_comments)
            self._perfmon_put(idx, time.monotonic() - tm)

        # И дальше забираем посты и комменты по дням, сортируя их строго по времени
        for source_perf, source_perf_threaded, posts, comments in iter_messages_threaded(
            min_date, max_date, self.source
        ):
            self._source_perf += source_perf
            self._source_perf_threaded += source_perf_threaded

            for post in posts:
                if post.created_at.tzinfo is None:
                    raise ValueError("Post.created_at must be aware datetime")
                post.created_at_local = post.created_at.astimezone(self.tz)

            for comment in comments:
                if comment.created_at.tzinfo is None:
                    raise ValueError("Comment.created_at must be aware datetime")
                comment.created_at_local = comment.created_at.astimezone(self.tz)

            messages: list[types.Post | types.Comment] = []
            messages.extend(posts)
            messages.extend(comments)

            if messages:
                messages.sort(key=lambda x: x.created_at)

            for idx, p in enumerate(self._processors):
                tm = time.monotonic()
                for message in messages:
                    if isinstance(message, types.Comment):
                        p.process_comment(message)
                    else:
                        p.process_post(message)
                self._perfmon_put(idx, time.monotonic() - tm)

            if drawer is not None:
                drawer.add_progress(len(messages))

        for idx, p in enumerate(self._processors):
            tm = time.monotonic()
            p.end_messages(stat_posts, stat_comments)
            self._perfmon_put(idx, time.monotonic() - tm)

        if drawer is not None:
            drawer.add_progress(0, force=True)

        self.log(1, f"| Done in {utils.format_timedelta(time.monotonic() - all_tm)}.")


def iter_messages(
    min_date: datetime,
    max_date: datetime,
    source: BaseDataSource,
    *,
    interval_days: int = 1,
) -> Iterator[tuple[float, list[types.Post], list[types.Comment]]]:
    # Загружаем посты и комменты небольшими кусочками по дням
    day = min_date
    while True:
        next_day = day + timedelta(days=interval_days)

        filters = {"created_at__gte": day}
        if next_day >= max_date:
            # max_date здесь это дата последнего поста/комментария, а не дата
            # из настроек, поэтому lte вместо lt
            filters["created_at__lte"] = max_date
        else:
            filters["created_at__lt"] = next_day

        tm = time.monotonic()

        # Опция burst, если реализована в источнике данных, позволяет ему не возиться
        # с итерацией и отдать все данные сразу одним куском
        posts = list(chain.from_iterable(source.iter_posts(filters=filters, burst=True)))
        comments = list(chain.from_iterable(source.iter_comments(filters=filters, burst=True)))

        source_perf = time.monotonic() - tm

        yield source_perf, posts, comments

        if next_day >= max_date:
            break
        day = next_day


def iter_messages_threaded(
    min_date: datetime,
    max_date: datetime,
    source: BaseDataSource,
    *,
    interval_days: int = 1,
    queue_size: int = 4,
) -> Iterator[tuple[float, float, list[types.Post], list[types.Comment]]]:
    # Поскольку куча времени тратится на ожидание данных от источника данных,
    # запуск этого ожидания в отдельном потоке позволяет ускорить работу

    tm = time.monotonic()

    # None в очереди означает завершение работы потока
    queue: "Queue[tuple[float, list[types.Post], list[types.Comment]] | None]" = Queue(queue_size)

    # Сигнал завершения для потока
    stopping = False

    # Ошибка, возникшая в потоке
    exc: BaseException | None = None

    def thread_func() -> None:
        nonlocal exc

        try:
            # Поток просто добавляет объекты из источника данных в очередь
            for item in iter_messages(min_date, max_date, source, interval_days=interval_days):
                if stopping:
                    break
                queue.put(item)

        except BaseException as e:  # pylint: disable=broad-exception-caught
            exc = e

        finally:
            # В конце всегда добавляем None как индикатор завершения работы потока
            queue.put(None)

    t = Thread(target=thread_func)
    t.start()

    done = False
    try:
        while True:
            if exc is not None:
                raise exc

            item = queue.get()
            if item is None:
                done = True
                break
            yield (time.monotonic() - tm,) + item
            tm = time.monotonic()

        if exc is not None:
            raise exc

    finally:
        # Отправляем потоку сигнал завершения работы
        stopping = True
        # Если поток ещё работает, нужно забирать данные из очереди, чтобы
        # случайно не словить зависание на переполненной очереди
        while not done and queue.get() is not None:
            pass
        t.join()
