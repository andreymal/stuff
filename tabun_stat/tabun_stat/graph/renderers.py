import csv
from pathlib import Path
from typing import Collection, Sequence, TypedDict

from tabun_stat.graph.charts import CustomPlot
from tabun_stat.graph.config import GraphConfig


class GraphData(TypedDict):
    title: str
    data: list[float]


def render_plot(
    config: GraphConfig,
    *,
    source: str,
    destination: str,
    width: int,
    height: int,
    graph_title: str = "",
    graph_subtitle: str = "",
    x_title: str = "",
    x_min: str | float | None = None,
    x_max: str | float | None = None,
    x_format: str | None = None,
    scale_x_integers: bool = False,
    scale_x_divisions: float | None = None,
    show_x_guidelines: bool = True,
    x_extra_guidelines: int = 0,
    rotate_x_labels: bool = False,
    x_column: str | None = None,
    x_are_strings: bool = False,
    y_title: str = "",
    y_min: float | None = None,
    y_max: float | None = None,
    y_format: str | None = None,
    scale_y_integers: bool = False,
    scale_y_divisions: float | None = None,
    show_y_guidelines: bool = True,
    y_extra_guidelines: int = 0,
    y_axis_right: bool = False,
    area_fill: bool = False,
    reverse: bool = False,
    only_columns: Collection[str] | None = None,
    skip_columns: Collection[str] | None = None,
    draw_legend: bool = True,
    legend_ingraph_position: float | None = None,
    colors: Sequence[str] | None = None,
    data_colors: dict[str, str] | None = None,
    data_dasharrays: dict[str, str] | None = None,
) -> None:
    """Простая рисовалка линейного графика по числам из csv-файла.

    :param config: настройки tabun_stat_graph
    :param source: исходный csv-файл
    :param destination: выходной svg-файл
    :param width: общая ширина картинки (с учётом всех полей и подписей)
    :param height: общая высота картинки (с учётом всех полей и подписей)
    :param graph_title: основной заголовок над графиком
    :param graph_subtitle: подзаголовок под основным заголовком
    :param x_title: заголовок оси X
    :param x_min: свой минимум по оси X на графике (число или строка
      в зависимости от x_are_strings)
    :param x_max: свой максимум по оси X на графике (число или строка
      в зависимости от x_are_strings)
    :param x_format: своё форматирование чисел по оси X (только если не задан
      x_are_strings)
    :param scale_x_integers: использовать только целые числа для сетки на оси X
    :param scale_x_divisions: шаг сетки по оси X
    :param show_x_guidelines: нарисовать сетку для значений на оси X
    :param x_extra_guidelines: число дополнительных линий между линиями основной
      сетки для оси X
    :param rotate_x_labels: повернуть подписи к оси X на 90 градусов
    :param x_column: название столбца, содержащего значения по оси X
      (по умолчанию первый столбец, все остальные столбцы идут в ось Y)
    :param x_are_strings: не пытаться интерпретировать значения X как числа
    :param y_title: заголовок оси Y
    :param y_min: свой минимум по оси Y на графике
    :param y_max: свой максимум по оси Y на графике
    :param y_format: своё форматирование чисел по оси Y
    :param scale_y_integers: использовать только целые числа для сетки на оси Y
    :param scale_y_divisions: шаг сетки по оси Y
    :param show_y_guidelines: нарисовать сетку для значений на оси Y
    :param y_extra_guidelines: число дополнительных линий между линиями основной
      сетки для оси Y
    :param y_axis_right: продублировать ось Y справа от графика
    :param area_fill: залить цветом области под графиками
    :param reverse: изменить порядок графиков на обратный (полезно, если они
      перекрывают друг друга при включенном area_fill; цвета при этом остаются
      как и без изменения порядка)
    :param only_columns: список столбцов, которые нужно добавлять в график
      (если указан, то остальные столбцы будут проигнорированы)
    :param skip_columns: список столбцов, которые не нужно добавлять в график
    :param draw_legend: рисовать ли легенду
    :param legend_ingraph_position: число, которое, если указано, переносит
      легенду внутрь графика и задаёт её выравнивание по горизонтали
      (от 0 до 1)
    :param colors: CSS-цвета графиков, используемые по умолчанию
    :param data_colors: словарь, переопределяющий цвета для отдельных столбцов
    :param data_dasharrays: словарь, переопределяющий stroke-dasharray
    для отдельных столбцов
    """

    with (Path(config.source) / source).open("r", encoding="utf-8-sig") as fp:
        reader = csv.reader(fp)
        headers = next(reader)
        rows = list(reader)

    if x_column is not None:
        x_col_id = headers.index(x_column)
    else:
        x_col_id = 0

    plot = CustomPlot(
        {
            "width": width,
            "height": height,
            "graph_title": graph_title,
            "show_graph_title": bool(graph_title),
            "graph_subtitle": graph_subtitle,
            "show_graph_subtitle": bool(graph_subtitle),
            "x_title": x_title,
            "show_x_title": bool(x_title),
            "x_format": x_format,
            "scale_x_integers": scale_x_integers,
            # scale_x_divisions ниже
            "show_x_guidelines": show_x_guidelines,
            "x_extra_guidelines": x_extra_guidelines,
            "rotate_x_labels": rotate_x_labels,
            "y_title": y_title,
            "show_y_title": bool(y_title),
            "min_y_value": y_min,
            "max_y_value": y_max,
            "y_format": y_format,
            "scale_y_integers": scale_y_integers,
            "scale_y_divisions": scale_y_divisions,
            "show_y_guidelines": show_y_guidelines,
            "y_extra_guidelines": y_extra_guidelines,
            "y_axis_right": y_axis_right,
            "area_fill": area_fill,
            "key": draw_legend,
            "key_position": "right",
            "legend_ingraph_position": legend_ingraph_position,
            "show_data_points": False,
            "show_data_values": False,
        },
    )

    # Конкретно это через словарь в конструкторе не работает, потому что property
    plot.scale_x_divisions = scale_x_divisions

    # Настраиваем подписи на оси X
    if x_are_strings:
        plot.x_labels = [row[x_col_id] for row in rows]
        plot.scale_x_integers = True

    if not colors:
        colors = CustomPlot.colors

    final_data: list[GraphData] = []
    final_colors = []
    final_dasharrays = {}

    # Каждый столбец, кроме столбца для оси X — отдельный график
    next_color_idx = 0
    for col_idx, col in enumerate(headers):
        if col_idx == x_col_id:
            continue
        if only_columns is not None and col not in only_columns:
            continue
        if skip_columns is not None and col in skip_columns:
            continue

        # Собираем данные в формат, пригодный для svg.charts
        # (в одном списке чередуются координаты X и Y)
        data: list[float] = []

        for row_idx, row in enumerate(rows):
            if x_are_strings:
                x = float(row_idx)
            else:
                x = float(row[x_col_id])

            if x_min is not None:
                if x_are_strings and isinstance(x_min, str):
                    if row[x_col_id] < x_min:
                        continue
                elif not x_are_strings and isinstance(x_min, float):
                    if x < x_min:
                        continue

            if x_max is not None:
                if x_are_strings and isinstance(x_max, str):
                    if row[x_col_id] > x_max:
                        continue
                elif not x_are_strings and isinstance(x_max, float):
                    if x > x_max:
                        continue

            y = float(row[col_idx])
            data.append(x)
            data.append(y)

        final_data.append({"title": col, "data": data})

        # Выбираем цвет графика
        if data_colors is not None and col in data_colors:
            color = data_colors[col]
            if color in colors:
                # Предотвращаем соседство одинаковых цветов
                next_color_idx = colors.index(color) + 1
        else:
            color = colors[next_color_idx % len(colors)]
            next_color_idx += 1
        final_colors.append(color)

        # И стиль линии
        if data_dasharrays is not None and col in data_dasharrays:
            final_dasharrays[len(final_colors) - 1] = data_dasharrays[col]

    if reverse:
        final_data.reverse()
        final_colors.reverse()
        final_dasharrays = {len(final_data) - k - 1: v for k, v in final_dasharrays.items()}

    for d in final_data:
        plot.add_data(d)
    plot.colors = final_colors
    plot.dasharrays = final_dasharrays

    # Генерируем готовый SVG
    svg = plot.burn()

    # И сохраняем в файл
    dst = Path(config.destination) / destination
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as fp:
        fp.write('<?xml version="1.0" encoding="utf-8"?>\n')
        fp.write(svg)
