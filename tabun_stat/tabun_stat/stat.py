#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List, Union

import pytz

from tabun_stat import utils
from tabun_stat.datasource.base import BaseDataSource
from tabun_stat.processors.base import BaseProcessor



class TabunStat:
    def __init__(
        self, source: BaseDataSource, destination: str, verbosity: int = 0,
        min_date: Optional[datetime] = None, max_date: Optional[datetime] = None,
        timezone: Union[str, utils.BaseTzInfo, None] = None
    ) -> None:
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
            self.timezone = pytz.timezone('UTC')
        else:
            self.timezone = timezone

        # Проверяем адекватность дат
        if self.min_date and self.max_date and self.max_date < self.min_date:
            raise ValueError('min_date is less than max_date')

        if os.path.exists(self.destination) and os.listdir(self.destination):
            raise OSError('Directory {!r} is not empty'.format(self.destination))

        self.log = self._default_log  # type: Callable
        self._isatty = None  # type: Optional[bool]

        self._processors = []  # type: List[BaseProcessor]
        self._perf = []  # type: List[float]
        self._source_perf = 0.0

    def _default_log(self, verbosity: int, *args, end: str = '\n', for_tty: bool = False) -> None:
        if verbosity > self.verbosity:
            return
        if not args or args == ('',):
            return
        if for_tty:
            if self._isatty is None:
                self._isatty = sys.stderr.isatty()
            if not self._isatty:
                return

        print(*args, file=sys.stderr, end=end, flush=True)

    def _empty_log(self, verbosity: int, *args, end: str = '\n', for_tty: bool = False) -> None:
        pass

    def set_log_function(self, func: Callable) -> None:
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

    def destroy(self):
        """Прибирает оперативку."""
        self._processors = []
        self.source = None

    # Замерялка производительности

    def _perfmon_reset(self) -> None:
        self._perf = [0.0] * len(self._processors)
        self._source_perf = 0.0

    def _perfmon_put(self, idx: int, duration: float) -> None:
        self._perf[idx] += duration

    def _print_perf_info(self, full_duration: Optional[float] = None) -> None:
        source_dur_str = '{:.1f}'.format(self._source_perf)
        rjust = len(source_dur_str)

        etc_dur_str = None  # type: Optional[str]
        if full_duration is not None:
            etc_duration = full_duration - sum(self._perf) - self._source_perf
            etc_dur_str = '{:.1f}'.format(etc_duration)

        if etc_dur_str and len(etc_dur_str) > rjust:
            rjust = len(etc_dur_str)

        for duration, p in sorted(zip(self._perf, self._processors), key=lambda x: x[0], reverse=True):
            dur_str = '{:.1f}'.format(duration)
            if len(dur_str) > rjust:
                rjust = len(dur_str)
            else:
                dur_str = dur_str.rjust(rjust)
            self.log(1, '{}s {}'.format(dur_str, type(p).__name__))

        self.log(1, '{}s source queries'.format(source_dur_str.rjust(rjust)))
        if etc_dur_str is not None:
            self.log(1, '{}s other'.format(etc_dur_str.rjust(rjust)))

    # Но сверху это всё вспомогательная вода, самая мякотка тут ↓

    def go(self):
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
        started_at_unix = time.time()
        self._perfmon_reset()
        self.log(1, 'tabun_stat started at {} UTC'.format(started_at.strftime('%Y-%m-%d %H:%M:%S')))

        # Определяемся с охватываемым периодом времени. Если максимальная дата
        # не указано, то явно прописываем текущую дату для большей
        # консистентности статистики (чтобы новые посты и комменты, появившиеся
        # уже во время подсчёта статистики, не испортили тут всё)
        min_date = self.min_date
        max_date = self.max_date
        if not max_date and (not min_date or started_at > min_date):
            max_date = started_at

        # Уведомляем о периоде пользователя
        self.log(1, 'Date interval for posts and comments (UTC): [{} .. {})'.format(
            min_date.strftime('%Y-%m-%d %H:%M:%S') if min_date else '-inf',
            max_date.strftime('%Y-%m-%d %H:%M:%S') if max_date else '+inf',
        ))

        # Составляем фильтр для источника
        # (сама максимальная дата в правый край диапазона не входит)
        datefilters = {'created_at__lt': max_date}
        if min_date:
            datefilters['created_at__gte'] = min_date

        # Создаём каталог, в который будет сгружена статистика
        if not os.path.isdir(self.destination):
            os.makedirs(self.destination)
        elif os.listdir(self.destination):
            raise OSError('Directory {!r} is not empty'.format(self.destination))

        # И дальше просто обрабатываем по очереди
        finished_at = None  # type: Optional[datetime]

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
            self.log(1, '\nInterrupted')

        finally:
            self.log(1, 'Finishing:', end='           ')
            drawer = utils.progress_drawer(target=len(self._processors), show_count=True, use_unicode=True)
            self.log(2, drawer.send(None) or '', end='', for_tty=True)

            for idx, p in enumerate(self._processors):
                self.log(2, drawer.send(idx + 1) or '', end='', for_tty=True)
                tm = time.time()
                p.stop()
                self._perfmon_put(idx, time.time() - tm)

            try:
                drawer.send(None)
            except StopIteration:
                pass
            self.log(1, '| Done.')

        if finished_at is not None:
            finished_at_unix = time.time()
            self.log(1, 'tabun_stat finished at {} UTC ({})'.format(
                finished_at.strftime('%Y-%m-%d %H:%M:%S'),
                utils.format_timedelta(finished_at - started_at),
            ))

            if self.verbosity >= 1:
                self.log(1, '\nPerformance info:')
                self._print_perf_info(finished_at_unix - started_at_unix)

    def _process_users(self, datefilters: Dict[str, Any]) -> None:
        self.log(1, 'Processing users:', end='    ')

        tm = time.time()
        stat = self.source.get_users_limits()
        self._source_perf += (time.time() - tm)

        if not stat['count']:
            self.log(1, 'nothing to do.')
            return

        drawer = utils.progress_drawer(target=stat['count'], show_count=True, use_unicode=True)
        self.log(2, drawer.send(None) or '', end='', for_tty=True)

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.begin_users(stat)
            self._perfmon_put(idx, time.time() - tm)

        i = 0
        tm = time.time()
        for users in self.source.iter_users():  # никакая сортировка не гарантируется
            self._source_perf += (time.time() - tm)
            for user in users:
                user['registered_at_local'] = utils.apply_tzinfo(user['registered_at'], self.timezone)

            i += len(users)
            self.log(2, drawer.send(i) or '', end='', for_tty=True)

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

        self.log(1, '| Done in {}.'.format(utils.format_timedelta(time.time() - tm)))

    def _process_blogs(self, datefilters: Dict[str, Any]) -> None:
        self.log(1, 'Processing blogs:', end='    ')

        tm = time.time()
        stat = self.source.get_blogs_limits()
        self._source_perf += (time.time() - tm)

        if not stat['count']:
            self.log(1, 'nothing to do.')
            return

        drawer = utils.progress_drawer(target=stat['count'], show_count=True, use_unicode=True)
        self.log(2, drawer.send(None) or '', end='', for_tty=True)

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.begin_blogs(stat)
            self._perfmon_put(idx, time.time() - tm)

        i = 0
        tm = time.time()
        for blogs in self.source.iter_blogs():  # никакая сортировка не гарантируется
            self._source_perf += (time.time() - tm)
            for blog in blogs:
                blog['created_at_local'] = utils.apply_tzinfo(blog['created_at'], self.timezone)

            i += len(blogs)
            self.log(2, drawer.send(i) or '', end='', for_tty=True)
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

        self.log(1, '| Done in {}.'.format(utils.format_timedelta(time.time() - tm)))

    def _process_posts_and_comments(self, datefilters: Dict[str, Any]) -> None:
        self.log(1, 'Processing messages:', end=' ')

        l = '(fetch stat...)'
        self.log(1, l, end='', for_tty=True)

        tm = time.time()
        stat_posts = self.source.get_posts_limits(filters=datefilters)
        stat_comments = self.source.get_comments_limits(filters=datefilters)
        self._source_perf += (time.time() - tm)

        self.log(1, '\b' * len(l), end='', for_tty=True)
        del l

        #{'first_created_at': None, 'last_created_at': None, 'count': 0}#

        # Если нет ни постов, ни комментов, то делать нечего
        if (
            (stat_posts['first_created_at'] is None or stat_posts['last_created_at'] is None or not stat_posts['count'])
            and
            (stat_comments['first_created_at'] is None or stat_comments['last_created_at'] is None or not stat_comments['count'])
        ):
            self.log(1, 'nothing to do.')
            return

        drawer = utils.progress_drawer(target=stat_posts['count'] + stat_comments['count'], show_count=True, use_unicode=True)
        self.log(2, drawer.send(None) or '', end='', for_tty=True)

        # Высчитываем охватываемый интервал времени
        if stat_posts['first_created_at'] and stat_comments['first_created_at']:
            min_date = min(stat_posts['first_created_at'], stat_comments['first_created_at'])
        else:
            min_date = stat_posts['first_created_at'] or stat_comments['first_created_at']

        if stat_posts['last_created_at'] and stat_comments['last_created_at']:
            max_date = max(stat_posts['last_created_at'], stat_comments['last_created_at'])
        else:
            max_date = stat_posts['last_created_at'] or stat_comments['last_created_at']

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.begin_messages(stat_posts, stat_comments)
            self._perfmon_put(idx, time.time() - tm)

        # И дальше забираем посты и комменты по дням, сортируя их строго по времени
        day = min_date
        i = 0
        while True:
            next_day = day + timedelta(days=1)
            assert not next_day.tzinfo

            filters = {'created_at__gte': day}
            if next_day >= max_date:
                filters['created_at__lte'] = max_date
            else:
                filters['created_at__lt'] = next_day

            tm = time.time()
            posts = []  # type: List[Dict[str, Any]]
            posts = sum(self.source.iter_posts(filters=filters), posts)
            comments = []  # type: List[Dict[str, Any]]
            comments = sum(self.source.iter_comments(filters=filters), comments)
            self._source_perf += (time.time() - tm)

            messages = posts + comments
            messages.sort(key=lambda x: x['created_at'])
            if messages:
                assert messages[0]['created_at'] >= day
                assert messages[-1]['created_at'] < next_day

            for message in messages:
                message['created_at_local'] = utils.apply_tzinfo(message['created_at'], self.timezone)

            for idx, p in enumerate(self._processors):
                tm = time.time()
                for message in messages:
                    if 'comment_id' in message:
                        p.process_comment(message)
                    else:
                        p.process_post(message)
                self._perfmon_put(idx, time.time() - tm)

            i += len(messages)
            self.log(2, drawer.send(i) or '', end='', for_tty=True)

            if next_day >= max_date:
                break
            day = next_day

        for idx, p in enumerate(self._processors):
            tm = time.time()
            p.end_messages(stat_posts, stat_comments)
            self._perfmon_put(idx, time.time() - tm)

        try:
            drawer.send(None)
        except StopIteration:
            pass

        self.log(1, '| Done in {}.'.format(utils.format_timedelta(time.time() - tm)))
        return
