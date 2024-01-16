# mypy: disable-error-code="no-any-return"

import copy
import importlib.resources
import math
from typing import Sequence

import cssutils  # type: ignore
from lxml import etree
from svg.charts.plot import Plot  # type: ignore

CSS_DIR = importlib.resources.files("tabun_stat.graph") / "css"


class CustomPlot(Plot):  # type: ignore[misc]
    """Рисовалка графиков из svg.charts, слегка пропатченная под нужды tabun_stat."""

    # Не-ноль создаёт уродские поля на графике
    font_size = 0.0

    # Покрупнее шрифты по умолчанию
    title_font_size = 24
    subtitle_font_size = 18
    x_label_font_size = 16
    x_title_font_size = 18
    y_label_font_size = 16
    y_title_font_size = 18
    key_font_size = 16

    # Подмена значений по оси X на строки из этого списка
    x_labels: list[str] | None = None

    # Произвольное форматирование чисел на осях
    x_format: str | None = None
    y_format: str | None = None

    # Дополнительные сеточки
    x_extra_guidelines = 0
    y_extra_guidelines = 0

    # Дублирование оси Y справа от графика
    y_axis_right = False

    # Размещение легенды сверху внутри графика
    legend_ingraph_position: float | None = None

    # Настраиваемые поля вокруг легенды
    legend_margin = 5
    legend_padding = 5

    # CSS-цвета графиков
    colors: Sequence[str] = [
        "#f00",
        "#00f",
        "#008000",
        "#fb0",
        "#0cf",
        "#f0f",
        "#0ff",
        "#ee0",
        "#c66",
        "#639",
        "#792",
        "#96f",
    ]

    # Переопределение стиля линий по их индексам
    dasharrays: dict[int, str] | None = None

    def _get_root_attributes(self) -> dict[str, str]:
        attrs = super()._get_root_attributes()

        # Я не знаю зачем это, уберу на всякий случай
        attrs.pop("{http://ns.adobe.com/AdobeSVGViewerExtensions/3.0/}scriptImplementation", None)

        # https://jwatt.org/svg/authoring/#doctype-declaration
        attrs["version"] = "1.1"
        attrs["baseProfile"] = "full"

        return attrs

    @staticmethod
    def load_resource_stylesheet(  # pylint: disable=dangerous-default-value
        name: str,
        subs: dict[str, object] = {},
    ) -> cssutils.css.CSSStyleSheet:
        # Вместо стандартных стилей svg.charts загружаем свои собственные
        template = (CSS_DIR / name).read_text(encoding="utf-8-sig")
        source = template % subs
        return cssutils.parseString(source)

    def get_stylesheet_resources(self) -> list[cssutils.css.CSSStyleSheet]:
        sheets = super().get_stylesheet_resources()

        # Генерируем CSS-код для цветов и стилей линий графиков

        colors_sheet = cssutils.css.CSSStyleSheet()
        for color_idx, color in enumerate(self.colors):
            colors_sheet.add(f".line{color_idx + 1} {{ stroke: {color}; }}")
            colors_sheet.add(f".fill{color_idx + 1} {{ fill: {color}; }}")
            colors_sheet.add(f".key{color_idx + 1} {{ fill: {color}; }}")

        if self.dasharrays is not None:
            for color_idx, dasharray in self.dasharrays.items():
                colors_sheet.add(f".line{color_idx + 1} {{ stroke-dasharray: {dasharray}; }}")

        sheets.append(colors_sheet)

        return sheets

    def get_x_labels(self) -> list[str]:
        if self.x_labels is not None:
            return [self.x_labels[int(x)] for x in self.get_x_values()]
        if self.x_format is not None:
            return [self.x_format.format(x) for x in self.get_x_values()]
        return super().get_x_labels()

    def get_y_labels(self) -> list[str]:
        if self.y_format is not None:
            return [self.y_format.format(y) for y in self.get_y_values()]
        return super().get_y_labels()

    def data_min(self, axis: str) -> float:
        # В стандартном svg.charts пользовательские лимиты мягкие (не обрезают график),
        # а я хочу именно что обрезать некоторые графики
        override_min = getattr(self, f"min_{axis}_value")
        if override_min is not None:
            return override_min

        min_value = super().data_min(axis)
        # Если указан scale_y_divisions, то выравниваем график под него
        if axis == "y" and self.scale_y_divisions:
            k = math.floor(min_value / self.scale_y_divisions)
            min_value = self.scale_y_divisions * k
        return min_value

    def data_max(self, axis: str) -> float:
        override_max = getattr(self, f"max_{axis}_value")
        if override_max is not None:
            return override_max

        max_value = super().data_max(axis)
        # Если указан scale_y_divisions, то выравниваем график под него
        if axis == "y" and self.scale_y_divisions:
            k = math.ceil(max_value / self.scale_y_divisions)
            max_value = self.scale_y_divisions * k
        return max_value

    def draw_graph(self) -> None:
        super().draw_graph()

        # Из-за особенностей координат в SVG линии получаются мыльными;
        # сдвигаем всё на полпикселя для получения чёткой картинки
        self.graph.set("transform", f"translate({int(self.border_left) + 0.5}, {int(self.border_top) + 0.5})")

        graphbg = self.graph.xpath("./rect[@class='graphBackground']")[0]
        graphbg.set("x", str(float(graphbg.get("x")) + 0.5))
        graphbg.set("y", str(float(graphbg.get("y")) + 0.5))

        x_axis = self.graph.xpath("./path[@id='xAxis']")[0]
        x_axis.set("transform", "translate(0 0.5)")

        y_axis = self.graph.xpath("./path[@id='yAxis']")[0]
        y_axis.set("transform", "translate(0.5 0)")

        if self.y_axis_right:
            etree.SubElement(
                self.graph,
                "path",
                {
                    "d": f"M {self.graph_width} 0 v{self.graph_height}",
                    "class": "axis",
                    "id": "xAxisRight",
                    "transform": "translate(0 0.5)",
                },
            )

    def draw_x_title(self) -> None:
        super().draw_x_title()

        if self.rotate_x_labels:
            # Баг в svg.charts: при повёрнутых подписях он правильно резервирует
            # место, но забывает сместить заголовок оси; смещаем сами
            longest_label_length = max(len(x) for x in self.get_x_labels())
            max_x_label_height_px = self.x_label_font_size * longest_label_length * 0.6

            text = self.root[-1]
            y = float(text.get("y"))
            y += max_x_label_height_px
            y -= self.x_label_font_size  # Отменяем стандартное резервирование места
            text.set("y", str(y))

    def draw_x_guidelines(self, label_height: float, count: int) -> None:
        if not self.show_x_guidelines:
            return
        for i in range(count):
            x = label_height * i
            if i != 0:
                # Отличие 1: int и 0.5 для немыльного отображения
                move = f"M {int(x + 0.5)} 0.5 v{self.graph_height - 1.0}"
                path = {"d": move, "class": "guideLines"}
                etree.SubElement(self.graph, "path", path)

            # Отличие 2: дополнительные линии
            for subx in range(1, self.x_extra_guidelines + 1):
                subxf = label_height * (subx / (self.x_extra_guidelines + 1))
                if x + subxf >= self.graph_width:
                    break
                move = f"M {int(x + subxf + 0.5)} 0.5 v{self.graph_height - 0.5}"
                path = {"d": move, "class": "guideLinesExtra"}
                etree.SubElement(self.graph, "path", path)

    def draw_y_guidelines(self, label_height: float, count: int) -> None:
        if not self.show_y_guidelines:
            return
        for i in range(count):
            y = self.graph_height - label_height * i
            if i != 0:
                # Отличие 1: int и 0.5 для немыльного отображения
                move = f"M 0.5 {int(y + 0.5)} h{self.graph_width}"
                path = {"d": move, "class": "guideLines"}
                etree.SubElement(self.graph, "path", path)

            # Отличие 2: дополнительные линии
            for suby in range(1, self.y_extra_guidelines + 1):
                subyf = label_height * (suby / (self.y_extra_guidelines + 1))
                if y - subyf <= 0.0:
                    break
                move = f"M 0.5 {int(y - subyf + 0.5)} h{self.graph_width}"
                path = {"d": move, "class": "guideLinesExtra"}
                etree.SubElement(self.graph, "path", path)

    def draw_y_label(self, label: tuple[int, str]) -> None:
        super().draw_y_label(label)

        if self.font_size == 0.0:
            text = self.graph[-1]
            y = float(text.get("y"))
            y += self.y_label_font_size / 2
            text.set("y", str(y))

        if self.y_axis_right:
            text2 = copy.deepcopy(text)
            x_offset = self.graph_width + 3
            text2.set("x", str(x_offset))
            text2.set("style", "text-anchor: start")
            self.graph.append(text2)

    def _y_labels_width(self) -> float:
        max_y_label_len = max(len(x) for x in self.get_y_labels())
        return 0.6 * max_y_label_len * self.y_label_font_size

    def _legend_width(self, *, border_box: bool = True, margin_box: bool = False) -> float:
        max_key_len = max(len(x) for x in self.keys())
        w = max_key_len * self.key_font_size * 0.6
        w += self.KEY_BOX_SIZE
        if border_box or margin_box:
            w += self.legend_padding * 2
        if margin_box:
            w += self.legend_margin * 2
        return w

    def _legend_height(self, *, border_box: bool = True, margin_box: bool = False) -> float:
        num_keys = len(self.data)
        h = (self.KEY_BOX_SIZE * num_keys) + (num_keys * 5)
        if border_box or margin_box:
            h += self.legend_padding * 2
        if margin_box:
            h += self.legend_margin * 2
        return h

    def calculate_right_margin(self) -> None:
        br = 7.0

        if self.key and self.key_position == "right" and self.legend_ingraph_position is None:
            # Если легенда справа от графика, то резервируем место под неё
            br += self._legend_width(margin_box=True)

        if self.show_y_labels and self.y_axis_right:
            # Если ось Y дублируется, то резервируем место под неё
            br += self._y_labels_width()

        self.border_right = br  # pylint: disable=attribute-defined-outside-init

    def draw_legend(self) -> None:
        if not self.key:
            return
        super().draw_legend()

        group = self.root[-1]

        if self.legend_ingraph_position is not None and self.key_position == "right":
            # Перемещаем легенду внутрь графика
            x = (
                self.legend_padding
                + self.legend_margin
                + int(self.border_left)
                + int((self.graph_width - self._legend_width(margin_box=True)) * self.legend_ingraph_position)
            )
            y = self.legend_padding + self.legend_margin + float(self.border_top)
            group.set("transform", f"translate({x} {y})")

        elif self.key_position == "right" and self.y_axis_right:
            # Пересчитываем координаты, чтобы не пересекалось с подписями на оси Y
            x_offset = self.graph_width + self.border_left + self._y_labels_width() + 10
            y_offset = self.border_top + 20
            group.set("transform", f"translate({x_offset} {y_offset})")

        # А ещё добавляем фон с рамочкой (которую тоже нужно сместить на полпикселя для немыльного отображения)
        legend_bg = etree.Element("rect")
        legend_bg.set("class", "legendBackground")
        legend_bg.set("x", str(-self.legend_padding + 0.5))
        legend_bg.set("y", str(-self.legend_padding + 0.5))
        legend_bg.set("width", str(int(self._legend_width() + 0.5)))
        legend_bg.set("height", str(int(self._legend_height() + 0.5)))
        group.insert(0, legend_bg)
