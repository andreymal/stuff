from datetime import datetime, timedelta
from typing import IO, TypedDict

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


class StatCategory(TypedDict):
    label: str
    blogs: list[str]


class CommentsCountsProcessor(BaseProcessor):
    def __init__(
        self,
        *,
        categories: list[StatCategory],
        first_day: datetime,
        period: int = 7,
    ):
        super().__init__()

        if first_day.tzinfo is None:
            raise ValueError("CommentsCountsProcessor.first_day must be aware datetime")

        self._labels = ["Закрытые блоги"]

        # Здесь храним, какой категории какой блог принадлежит
        self._blogs_categories_slug: dict[str, int] = {}  # {blog_slug: category_idx}
        self._blogs_categories: dict[int, int] = {}  # {blog_id: category_idx}

        # Собираем категории из параметров
        for idx, item in enumerate(categories, 1):
            self._labels.append(item["label"])
            for slug in item["blogs"]:
                self._blogs_categories_slug[slug] = idx

        # Несколько предустановленных категорий
        self._labels.extend(
            [
                "Полузакрытые",
                "Личные блоги",
                "Открытые",
                "Всего комментариев согласно их номерам",
            ],
        )
        # И индексы для них
        self._closed_idx = 0
        self._semiclosed_idx = len(self._labels) - 4
        self._personal_idx = len(self._labels) - 3
        self._open_idx = len(self._labels) - 2
        self._all_by_id_idx = len(self._labels) - 1

        # Статистика по категориям
        self._stat = [0] * (len(self._labels) - 1)
        # Крайние комменты периода, для подсчёта всех существующих комментов
        # (с учётом неизвестных закрытых блогов и лички)
        # Сбрасываются в конце каждого периода
        self._first_comment_id = 0
        self._last_comment_id = 0

        # Период подсчёта статистики (по умолчанию неделя)
        self.period = period
        # С какого дня начинать считать статистику
        # (границы суток считаются с учётом часового пояса из настроек)
        self.period_begin = first_day
        self.period_end = self.period_begin  # Перезапишем в start

        self._fp: IO[str] | None = None
        self._fp_sum: IO[str] | None = None
        self._fp_perc: IO[str] | None = None

    def start(self, stat: TabunStat) -> None:
        super().start(stat)
        self._fp = (stat.destination / "comments_counts.csv").open("w", encoding="utf-8")
        self._fp_sum = (stat.destination / "comments_counts_sum.csv").open("w", encoding="utf-8")
        self._fp_perc = (stat.destination / "comments_counts_perc.csv").open("w", encoding="utf-8")

        # Применяем часовой пояс к периоду
        self.period_begin = self.period_end = self.period_begin.astimezone(stat.tz)
        # И начинаем первый период
        self._increment_period()

        header = ["Дата"] + self._labels
        header_csv = utils.csvline(*header)

        self._fp.write(header_csv)
        self._fp_sum.write(header_csv)
        self._fp_perc.write(utils.csvline(*header[:-1]))  # В процентах комменты из лички не учитываем

    def process_blog(self, stat: TabunStat, blog: types.Blog) -> None:
        if blog.slug in self._blogs_categories_slug:
            self._blogs_categories[blog.id] = self._blogs_categories_slug[blog.slug]

    def process_comment(self, stat: TabunStat, comment: types.Comment) -> None:
        # OLEG778!!!!!!!!
        if comment.id == 2498188:
            return

        # Если период закончился, то сохраняем статистику
        while comment.created_at >= self.period_end:
            self._flush_stat(stat)

        # Забираем граничные айдишники комментов, чтобы потом по ним угадать
        # общее число комментов
        if self._first_comment_id == 0 or self._last_comment_id == 0:
            self._first_comment_id = self._last_comment_id = comment.id
        elif comment.id > self._last_comment_id:
            self._last_comment_id = comment.id

        if comment.blog_status is None:
            return

        # Вычисляем категорию согласно настройкам
        blog_id = comment.blog_id
        blog_status = comment.blog_status
        category_idx = self._blogs_categories.get(blog_id) if blog_id is not None else None

        # Если в настройках ничего, то используем одну из встроенных категорий
        if category_idx is None:
            if blog_id is not None and blog_status == 1:
                category_idx = self._closed_idx
            elif blog_id is not None and blog_status == 2:
                category_idx = self._semiclosed_idx
            elif blog_id is None:
                category_idx = self._personal_idx
            else:
                assert blog_status == 0
                category_idx = self._open_idx

        # Пишем статистику в выбранную категорию
        self._stat[category_idx] += 1

    def _flush_stat(self, stat: TabunStat) -> None:
        # Собираем три разные строки для трёх файлов
        line: list[object] = [self.period_begin.strftime("%Y-%m-%d")]
        line_sum = line[:]
        line_perc = line[:]

        # Высчитываем, что такое 100%
        # Число комментов, доступных в базе данных
        all_exist_count = sum(self._stat)

        # Число комментов вместе с неизвестными, угаданное по id
        all_count = self._last_comment_id - self._first_comment_id + 1
        if self._last_comment_id == 0:
            all_count = 0
        if all_count < all_exist_count:
            stat.log(
                0,
                "WARNING comments_counts: inconsistent comments count:",
                f"all_count({all_count}) < all_exist_count({all_exist_count})!",
            )
            all_count = all_exist_count

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
            line_perc.append(f"{percent:.2f}")

        line.append(all_count)
        line_sum.append(all_count)
        # В line_perc all_count не используется

        # Пишем в файлы
        assert self._fp
        self._fp.write(utils.csvline(*line))
        assert self._fp_sum
        self._fp_sum.write(utils.csvline(*line_sum))
        assert self._fp_perc
        self._fp_perc.write(utils.csvline(*line_perc))

        # Обнуляем статистику для начала следующего периода
        self._stat = [0] * (len(self._labels) - 1)
        self._first_comment_id = self._last_comment_id = 0

        # Высчитываем следующий период
        self._increment_period()

    def _increment_period(self) -> None:
        self.period_begin = self.period_end
        # Теоретически есть шанс попасть в несуществующее или неоднозначное время... но пофиг наверное
        self.period_end = self.period_begin + timedelta(days=self.period)

    def stop(self, stat: TabunStat) -> None:
        if sum(self._stat) > 0:
            self._flush_stat(stat)

        if self._fp is not None:
            self._fp.close()
            self._fp = None
        if self._fp_sum is not None:
            self._fp_sum.close()
            self._fp_sum = None
        if self._fp_perc is not None:
            self._fp_perc.close()
            self._fp_perc = None
        super().stop(stat)
