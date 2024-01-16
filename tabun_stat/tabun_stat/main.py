import argparse
import sys

from tabun_stat import utils
from tabun_stat.config import Config
from tabun_stat.datasource.base import BaseDataSource
from tabun_stat.processors.base import BaseProcessor
from tabun_stat.stat import TabunStat


def load_datasource(params: dict[str, object]) -> BaseDataSource:
    kwargs = dict(params)
    source_name = str(kwargs.pop("name"))
    if source_name.startswith(":"):
        source_name = "tabun_stat.datasource." + source_name[1:]

    source_creator = utils.import_string(source_name)
    if not callable(source_creator):
        raise TypeError(f"{source_name} is not callable")

    source = source_creator(**kwargs)
    if not isinstance(source, BaseDataSource):
        raise TypeError(f"{source!r} is not a subclass of BaseDataSource")

    return source


def load_processor(params: dict[str, object]) -> BaseProcessor:
    kwargs = dict(params)
    processor_name = str(kwargs.pop("name"))
    if processor_name.startswith(":"):
        processor_name = "tabun_stat.processors." + processor_name[1:]

    processor_creator = utils.import_string(processor_name)
    if not callable(processor_creator):
        raise TypeError(f"{processor_name} is not callable")

    processor = processor_creator(**kwargs)
    if not isinstance(processor, BaseProcessor):
        raise TypeError(f"{processor!r} is not a subclass of BaseProcessor")

    return processor


def load_processors(params_list: list[dict[str, object]]) -> list[BaseProcessor]:
    processors = []
    for params in params_list:
        processors.append(load_processor(params))
    return processors


def main() -> int:
    parser = argparse.ArgumentParser(description="Statistics calculator for Tabun")
    parser.add_argument("-c", "--config", help="path to config file (TOML)", required=True)
    parser.add_argument("-o", "--destination", help="override destination directory", default=None)
    parser.add_argument("-v", "--verbosity", action="count", help="verbose output", default=0)

    args = parser.parse_args()

    config = Config.from_file(args.config)
    source = load_datasource(config.datasource)
    processors = load_processors(config.processors)

    stat = TabunStat(
        source=source,
        destination=args.destination or config.destination,
        verbosity=args.verbosity,
        min_date=config.min_date,
        max_date=config.max_date,
        tz=config.timezone,
    )
    for p in processors:
        stat.add_processor(p)

    stat.go()

    stat.destroy()
    source.destroy()

    return 0


if __name__ == "__main__":
    sys.exit(main())
