import time
import importlib
from datetime import datetime, timedelta
from typing import Any, List, Optional, Iterable, Generator, TypeVar, Union

import pytz

T = TypeVar("T")


def import_string(s: str) -> Any:
    if '.' not in s:
        raise ValueError('import_string can import only objects using dot')

    module_name, attr = s.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def csvline(
    *args: Any, end: str = '\n', delimeter: str = ',',
    quote: str = '"', always_quote: bool = False,
    slash_escape: bool = False
) -> str:
    """Возвращает строку, пригодную для записи в csv-файл.

    :param args: объекты для записи (будут приведены к строке)
    :param str end: что дописать в конец строки (по умолчанию перевод строки)
    :param str delimeter: разделитель объектов (по умолчанию запятая)
    :param str quote: кавычка, используемая для экранирования
    :param bool always_quote: оборачивать все объекты в кавычки, даже если
      нет необходимости
    :param bool slash_escape: экранировать кавычку слэшем, а не самой кавычкой
    :rtype: str
    """

    result = []  # type: List[str]

    for x in args:
        if result:
            result.append(delimeter)
        x = str(x)

        if always_quote or quote in x or '\n' in x:
            if slash_escape:
                x = x.replace(quote, '\\' + quote)
            else:
                x = x.replace(quote, quote + quote)
            x = quote + x + quote

        result.append(x)

    result.append(end)

    return ''.join(result)


def progress_drawer(
    target: int, w: int = 30, progress_chars: Optional[str] = None,
    lb: Optional[str] = None, rb: Optional[str] = None, humanize: bool = False,
    show_count: bool = False, fps: float = 25.0, use_unicode: bool = False
) -> Generator[Optional[str], Optional[int], None]:
    """Подготавливает всё для рисования полоски прогресса и возвращает
    сопрограмму, в которую следует передавать текущий прогресс.

    Суть такова:

    1. Вызываем функцию, передавая первым параметром target значение, которое
       будет считаться за 100%. Полученную сопрограмму сохраняем и запускаем
       вызовом ``send(None)``.

    2. При каждом обновлении передаём текущий прогресс через ``send(N)``.
       Функция посчитает проценты относительно target и возвратит полоску
       загрузки с управляющими ASCII-символами, пригодную для печати в stdout
       (если ранее уже рисовалась, то отрисует поверх старой).
       Чаще чем ``fps`` кадров в секунду не перерисовывает. Если fps ноль
       или меньше, то отрисовывает при каждом изменении.

    3. После завершения передаём прогресс, равный target (что даст 100%),
       а потом передаём None. Сопрограмма завершит работу и выкинет
       StopIteration.

    :param int target: число, которое будет считаться за 100%
    :param int w: длина полоски в символах (без учёта границы и процентов)
    :param str progress_chars: символы для рисования прогресса (первый —
       пустая часть, последний — полная часть, между ними — промежуточные
       состояния)
    :param str lb: левая граница полоски
    :param str rb: правая граница полоски
    :param bool humanize: при True выводит текущее значение в кибибайтах
       (делённое на 1024), при False как есть
    :param bool show_count: при True печатает также target
    :param float fps: максимально допустимая частота кадров. Работает так:
       если между двумя send частота получается больше чем fps, то один кадр
       не рисуется и пропускается, однако 100% для красоты никогда
       не пропускается
    :param bool use_unicode: использовать ли юникод на полную катушку
    """

    # Выбираем, какими символами будем рисовать полоску
    if not progress_chars:
        if use_unicode:
            progress_chars = ' ▏▎▍▌▋▊▉█'
        else:
            progress_chars = ' -#'
    if lb is None:
        lb = '▕' if use_unicode else ' ['
    if rb is None:
        rb = '▏' if use_unicode else '] '

    min_period = 0.0
    if fps > 0.0:
        min_period = 1.0 / fps  # для 25 fps это 0.04

    current = 0  # type: Optional[int]
    old_current = None  # type: Optional[int]
    old_line = ''

    tm = 0.0
    lastlen = 0

    while current is not None:
        text_for_print = None  # type: Optional[str]

        # Умная математика, сколько каких блоков выводить
        part = (current * 1.0 / target) if target > 0 else 1.0
        if part < 0.0:
            part = 0.0
        elif part > 1.0:
            part = 1.0

        full_blocks = int(part * w)
        empty_blocks = w - full_blocks - 1
        part_block_position = (part * w) - full_blocks
        part_block_num = int(part_block_position * (len(progress_chars) - 1))

        # Готовим строку с числовой информацией о прогрессе, чтобы вывести после полоски
        if show_count:
            if humanize:
                cnt_string = '({}K/{}K) '.format(int(current / 1024.0), int(target / 1024.0))
            else:
                cnt_string = '({}/{}) '.format(current, target)
        else:
            if humanize:
                cnt_string = '({}K) '.format(int(current / 1024.0))
            else:
                cnt_string = '({}) '.format(current)

        # Обновляем полоску:
        # - только когда значение новое
        # - не чаще 25 кадров в секунду, но только если текущее значение
        #   не совпадает с 100% (чтобы последний кадр гарантированно
        #   отрисовался)
        if current != old_current and (current == target or not min_period or time.time() - tm >= min_period):
            old_current = current

            # Собираем всю полоску
            line = lb
            line += progress_chars[-1] * full_blocks
            if full_blocks != w:
                line += progress_chars[part_block_num]
            line += progress_chars[0] * empty_blocks
            line += rb
            line += '{:.1f}% '.format(int(part * 1000) / 10.0).rjust(7)
            line += cnt_string

            # Печатаем её (только если полоска вообще изменилась)
            if line != old_line:
                old_line = line
                text_for_print = fprint_substring(line, lastlen)
                lastlen = len(line)

                # Запоминаем время печати для ограничения кадров в секунду
                if min_period:
                    tm = time.time()

        current = yield text_for_print


def fprint_substring(s: str, l: int = 0) -> str:
    """Возвращает строку, пригодную для печати с затиранием последних
    l символов.
    """

    result = []  # type: List[str]
    if l > 0:
        result.append('\b' * l)
    result.append(s)
    if len(s) < l:
        result.append(' ' * (l - len(s)))
        result.append('\b' * (l - len(s)))
    return ''.join(result)


def format_timedelta(tm: Union[int, float, timedelta]) -> str:
    if isinstance(tm, timedelta):
        tm = tm.total_seconds()
    tm = int(tm)

    minus = False
    if tm < 0:
        minus = True
        tm = -tm

    s = '{:02d}s'.format(tm % 60)
    if tm >= 60:
        s = '{:02d}m'.format((tm // 60) % 60) + s
    if tm >= 3600:
        s = '{}h'.format(tm // 3600) + s

    if minus:
        s = '-' + s
    return s


def apply_tzinfo(tm: datetime, tzinfo: Union[str, pytz.BaseTzInfo, None] = None) -> datetime:
    """Применяет часовой пояс ко времени, перематывая время на нужное число
    часов/минут.

    Если у переданного в функцию времени нет часового пояса, он считается UTC.
    Аргумент tzinfo может быть строкой с названием часового пояса;
    None считается за UTC.
    """

    if tzinfo and isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if not tzinfo:
        tzinfo = pytz.timezone('UTC')
    assert isinstance(tzinfo, pytz.BaseTzInfo)

    if not tm.tzinfo:
        tm = tzinfo.fromutc(tm)
    elif tm.tzinfo != tzinfo:
        tm = tzinfo.normalize(tm)
    return tm


def force_utc(tm: datetime) -> datetime:
    return apply_tzinfo(tm, pytz.timezone('UTC'))


def set_tzinfo(tm: datetime, tzinfo: Union[str, pytz.BaseTzInfo, None] = None, is_dst: bool = False) -> datetime:
    """Прикрепляет часовой пояс к объекту datetime, который без пояса.
    Возвращает объект datetime с прикреплённым часовым поясом, но значение
    (в частности, день и час), остаются теми же, что и были.
    Для конвертирования времени в нужный часовой пояс см. apply_tzinfo.
    Аргумент tzinfo может быть строкой с названием часового пояса;
    None считется за UTC.

    :param datetime tm: время (без часового пояса)
    :param tzinfo: часовой пояс, который надо прикрепить
    :param bool is_dst: в случае неоднозначностей (например,
      31 октября 2010-го 02:00 - 02:59 по Москве) указывает, считать это время
      летним (True) или зимним (False)
    :rtype: datetime
    """

    if tm.tzinfo:
        raise ValueError('datetime already has tzinfo')

    if tzinfo and isinstance(tzinfo, str):
        tzinfo = pytz.timezone(tzinfo)

    if not tzinfo:
        tzinfo = pytz.timezone('UTC')
    assert isinstance(tzinfo, pytz.BaseTzInfo)

    return tzinfo.localize(tm, is_dst=is_dst)


def append_days(tm: datetime, days: int) -> datetime:
    # Функция возможно будет баговать на некоторых особо хитрых часовых поясах,
    # но и так сойдёт, для Europe/Moscow работает и норм

    if not tm.tzinfo:
        return tm + timedelta(days=days)

    if not isinstance(tm.tzinfo, pytz.BaseTzInfo):
        raise ValueError('Expected pytz tzinfo')

    # Добавляем days*24 часов пока без учёта пояса
    tomorrow = tm + timedelta(days=days)
    # Нормализуем (час может измениться!)
    tomorrow = tm.tzinfo.normalize(tomorrow)
    # Выясняем, попадаются ли 25 часов в сутках между старой и новой датой
    tomorrow_utcoffset = tomorrow.utcoffset()
    tm_utcoffset = tm.utcoffset()
    assert tomorrow_utcoffset is not None
    assert tm_utcoffset is not None  # mypy hints
    diff = tomorrow_utcoffset - tm_utcoffset
    # Если есть, то компенсируем
    if diff:
        tomorrow -= diff

    assert tomorrow.hour == tm.hour
    assert tomorrow.minute == tm.minute
    return tomorrow

    # тест:
    # d = pytz.timezone('Europe/Moscow').localize(datetime(2014, 10, 26, 0, 0, 0))
    # d  # => 2014-10-26 00:00:00+04:00
    # append_days(d, 1)  # => 2014-10-27 00:00:00+03:00


def drop_duplicates(items: Iterable[T]) -> List[T]:
    result: List[T] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
