from datetime import datetime, timedelta
from typing import IO, TypedDict

from tabun_stat import types, utils
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


class StatCategory(TypedDict):
    label: str
    blogs: list[str]


class PostsCountsProcessor(BaseProcessor):
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
            ],
        )
        # И индексы для них
        self._closed_idx = 0
        self._semiclosed_idx = len(self._labels) - 3
        self._personal_idx = len(self._labels) - 2
        self._open_idx = len(self._labels) - 1

        # Статистика по категориям
        self._stat = [0] * len(self._labels)

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
        self._fp = (stat.destination / "posts_counts.csv").open("w", encoding="utf-8")
        self._fp_sum = (stat.destination / "posts_counts_sum.csv").open("w", encoding="utf-8")
        self._fp_perc = (stat.destination / "posts_counts_perc.csv").open("w", encoding="utf-8")

        # Применяем часовой пояс к периоду
        self.period_begin = self.period_end = self.period_begin.astimezone(stat.tz)
        # И начинаем первый период
        self._increment_period()

        header = ["Дата"] + self._labels
        header_csv = utils.csvline(*header)

        self._fp.write(header_csv)
        self._fp_sum.write(header_csv)
        self._fp_perc.write(utils.csvline(*header))

    def process_blog(self, stat: TabunStat, blog: types.Blog) -> None:
        if blog.slug in self._blogs_categories_slug:
            self._blogs_categories[blog.id] = self._blogs_categories_slug[blog.slug]

    def process_post(self, stat: TabunStat, post: types.Post) -> None:
        # Если период закончился, то сохраняем статистику
        while post.created_at >= self.period_end:
            self._flush_stat()

        # Вычисляем категорию согласно настройкам
        blog_id = post.blog_id
        blog_status = post.blog_status
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

    def _flush_stat(self) -> None:
        # Собираем три разные строки для трёх файлов
        line: list[object] = [self.period_begin.strftime("%Y-%m-%d")]
        line_sum = line[:]
        line_perc = line[:]

        # Высчитываем, что такое 100%
        # Число постов, доступных в базе данных
        # (достоверно посчитать число всех постов, в отличие от комментов,
        # нельзя, потому что дата создания/публикации поста может меняться)
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
            line_perc.append(f"{percent:.2f}")

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
        self._increment_period()

    def _increment_period(self) -> None:
        self.period_begin = self.period_end
        # Теоретически есть шанс попасть в несуществующее или неоднозначное время... но пофиг наверное
        self.period_end = self.period_begin + timedelta(days=self.period)

    def stop(self, stat: TabunStat) -> None:
        if sum(self._stat) > 0:
            self._flush_stat()

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
