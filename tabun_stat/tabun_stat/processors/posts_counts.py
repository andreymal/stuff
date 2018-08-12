#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Dict, Tuple, Any, Set, List, Optional, TextIO
from datetime import datetime, timedelta

from tabun_stat import utils
from tabun_stat.processors.base import BaseProcessor

from tabun_stat.stat import TabunStat


class PostsCountsProcessor(BaseProcessor):
    def __init__(self, categories: List[Dict[str, Any]], first_day: datetime, period: int = 7) -> None:
        super().__init__()

        self._labels = [
            'Закрытые блоги',
        ]

        # Здесь храним, какой категории какой блог принадлежит
        self._blogs_categories_slug = {}  # type: Dict[str, int]
        self._blogs_categories = {}  # type: Dict[int, int]

        # Собираем категории из параметров
        for idx, item in enumerate(categories, 1):
            self._labels.append(item['label'])
            for slug in item['blogs']:
                self._blogs_categories_slug[slug] = idx

        # Несколько предустановленных категорий
        self._labels.extend([
            'Полузакрытые',
            'Личные блоги',
            'Открытые',
        ])
        # И индексы для них
        self._closed_idx = 0
        self._halfclosed_idx = len(self._labels) - 3
        self._personal_idx = len(self._labels) - 2
        self._open_idx = len(self._labels) - 1

        # Статистика по категориям
        self._stat = [0] * len(self._labels)

        # Период подсчёта статистики (по умолчанию неделя)
        self.period = period
        # С какого дня начинать считать статистику
        # (границы суток считаются с учётом часового пояса из настроек)
        # (но даты здесь хранятся в UTC)
        self.period_begin = utils.force_utc(first_day).replace(tzinfo=None)
        self.period_end = self.period_begin.replace(tzinfo=None)  # Перезапишем в start

        self._fp = None  # type: Optional[TextIO]
        self._fp_sum = None  # type: Optional[TextIO]
        self._fp_perc = None  # type: Optional[TextIO]

    def _append_days(self, period_begin: datetime) -> datetime:
        assert self.stat
        period_begin_local = utils.apply_tzinfo(period_begin, self.stat.timezone)
        period_end_local = utils.append_days(period_begin_local, days=self.period)
        return utils.force_utc(period_end_local).replace(tzinfo=None)

    def start(
        self, stat: TabunStat,
        min_date: Optional[datetime] = None, max_date: Optional[datetime] = None
    ) -> None:
        super().start(stat, min_date, max_date)
        assert self.stat

        self._fp = open(os.path.join(self.stat.destination, 'posts_counts.csv'), 'w', encoding='utf-8')
        self._fp_sum = open(os.path.join(self.stat.destination, 'posts_counts_sum.csv'), 'w', encoding='utf-8')
        self._fp_perc = open(os.path.join(self.stat.destination, 'posts_counts_perc.csv'), 'w', encoding='utf-8')

        # Применяем часовой пояс к периоду
        self.period_end = self._append_days(self.period_begin)

        header = ['Первый день недели'] + self._labels
        header_csv = utils.csvline(*header)

        self._fp.write(header_csv)
        self._fp_sum.write(header_csv)
        self._fp_perc.write(utils.csvline(*header[:-1]))  # В процентах комменты из лички не учитываем

    def process_blog(self, blog: Dict[str, Any]) -> None:
        if blog['slug'] in self._blogs_categories_slug:
            self._blogs_categories[blog['blog_id']] = self._blogs_categories_slug[blog['slug']]

    def process_post(self, post: Dict[str, Any]) -> None:
        assert self.stat

        # Если период закончился, то сохраняем статистику
        assert self.period_end
        while post['created_at'] >= self.period_end:
            self._flush_stat()

        # Вычисляем категорию согласно настройкам
        blog_id = post['blog_id']
        category_idx = self._blogs_categories.get(blog_id) if blog_id is not None else None
        blog_status = self.stat.source.get_blog_status_by_id(blog_id)

        # Если в настройках ничего, то используем одну из встроенных категорий
        if category_idx is None:
            if blog_id is not None and blog_status == 1:
                category_idx = self._closed_idx
            elif blog_id is not None and blog_status == 2:
                category_idx = self._halfclosed_idx
            elif blog_id is None:
                category_idx = self._personal_idx
            else:
                assert blog_status == 0
                category_idx = self._open_idx

        # Пишем статистику в выбранную категорию
        self._stat[category_idx] += 1

    def _flush_stat(self) -> None:
        assert self.stat
        period_begin_local = utils.apply_tzinfo(self.period_begin, self.stat.timezone)

        # Собираем три разные строки для трёх файлов
        line = [period_begin_local.strftime('%Y-%m-%d')]  # type: List[Any]
        line_sum = line[:]  # type: List[Any]
        line_perc = line[:]  # type: List[Any]

        # Высчитываем, что такое 100%
        all_exist_count = sum(self._stat)

        # И собираем в строки данные по каждой категории
        cnt_sum = 0
        for cnt in self._stat:
            # В простой файл просто пишем число как есть
            line.append(cnt)
            # В файле с суммами используем складывание слева направо для более простого рисования графиков
            cnt_sum += cnt
            line_sum.append(cnt_sum)
            # Проценты тоже суммируем для удобства рисования графиков
            percent = 0.0 if all_exist_count <= 0 else (cnt_sum * 100.0 / all_exist_count)
            line_perc.append('{:.2f}'.format(percent))

        # Пишем в файлы
        assert self._fp
        self._fp.write(utils.csvline(*line))
        assert self._fp_sum
        self._fp_sum.write(utils.csvline(*line_sum))
        assert self._fp_perc
        self._fp_perc.write(utils.csvline(*line_perc))

        # Обнуляем статистику для начала следующего периода
        self._stat = [0] * len(self._labels)

        # Высчитываем следующий период
        self.period_begin = self.period_end
        self.period_end = self._append_days(self.period_begin)

    def stop(self) -> None:
        if sum(self._stat) > 0:
            self._flush_stat()

        if self._fp:
            self._fp.close()
            self._fp = None
        if self._fp_sum:
            self._fp_sum.close()
            self._fp_sum = None
        if self._fp_perc:
            self._fp_perc.close()
            self._fp_perc = None
        super().stop()
