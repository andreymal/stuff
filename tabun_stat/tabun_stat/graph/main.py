import argparse
import sys
import time

from tabun_stat import utils
from tabun_stat.graph.config import GraphConfig


def apply_inheritance(kwargs: dict[str, object], graphs: list[dict[str, object]]) -> dict[str, object]:
    graph_base = kwargs.pop("graph_base", None)
    if graph_base is None:
        return kwargs
    if not isinstance(graph_base, str):
        raise TypeError(f"graph_base must be string (got {graph_base!r})")

    # Ищем базовый график
    base_kwargs = None
    for x in graphs:
        if x.get("graph_name") == graph_base:
            if base_kwargs is not None:
                raise ValueError(f"Duplicate graph {graph_base!r}")
            base_kwargs = x
    if base_kwargs is None:
        raise ValueError(f"Base graph {graph_base!r} not found")

    # Если базовый график тоже наследуется от кого-то, то и его обрабатываем
    base_kwargs = dict(base_kwargs)
    base_kwargs = apply_inheritance(base_kwargs, graphs)

    # И применяем параметры базового графика к потомку
    final_kwargs = dict(base_kwargs)
    final_kwargs.pop("graph_name", None)
    final_kwargs.update(kwargs)
    assert "graph_base" not in final_kwargs
    return final_kwargs


def main() -> int:
    parser = argparse.ArgumentParser(description="Draws graphs for Tabun statistics")
    parser.add_argument("-c", "--config", help="path to graph config file (TOML)", required=True)
    parser.add_argument("-s", "--source", help="override stat source directory", default=None)
    parser.add_argument("-o", "--destination", help="override destination directory", default=None)
    parser.add_argument("-v", "--verbosity", action="count", help="verbose output", default=0)

    args = parser.parse_args()

    config = GraphConfig.from_file(args.config)

    for i, graph in enumerate(config.graph):
        kwargs = graph.copy()
        graph_name = kwargs.pop("graph_name", str(i))
        print(f"Rendering graph {graph_name}...", end=" ", flush=True)

        # Чтобы меньше дубликатить в конфиге, графики могут наследоваться от других графиков
        kwargs = apply_inheritance(kwargs, config.graph)

        start_time = time.monotonic()
        renderer_str = str(kwargs.pop("renderer"))
        if renderer_str.startswith(":"):
            renderer_str = "tabun_stat.graph.renderers." + renderer_str[1:]

        renderer = utils.import_string(renderer_str)
        if not callable(renderer):
            raise TypeError(f"{renderer_str} is not callable")

        renderer(config, **kwargs)
        duration = time.monotonic() - start_time

        print(f"Done in {duration:.1f}s.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
