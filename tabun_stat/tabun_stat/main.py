#!/usr/bin/env python3

import sys
import argparse
from typing import Callable

import toml

from tabun_stat.stat import TabunStat
from tabun_stat import utils
from tabun_stat.datasource.base import BaseDataSource
from tabun_stat.processors.base import BaseProcessor


__all__ = ['main']


def main() -> int:
    parser = argparse.ArgumentParser(description='Statistic calculator for Tabun')
    parser.add_argument('-c', '--config', help='path to config file (TOML)', required=True)
    parser.add_argument('-o', '--destination', help='override destination directory', default=None)
    parser.add_argument("-v", "--verbosity", action="count", help="verbose output", default=0)

    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8-sig') as fp:
        config = toml.load(fp)

    kwargs = dict(config['datasource'])
    source_name = kwargs.pop('name')
    if source_name.startswith(':'):
        source_name = 'tabun_stat.datasource.' + source_name[1:]
    source_creator: Callable[..., BaseDataSource] = utils.import_string(source_name)
    source = source_creator(**kwargs)

    processors = []
    for processor_data in config['processors']:
        kwargs = dict(processor_data)
        processor_name = kwargs.pop('name')
        if processor_name.startswith(':'):
            processor_name = 'tabun_stat.processors.' + processor_name[1:]
        processor_creator: Callable[..., BaseProcessor] = utils.import_string(processor_name)
        processors.append(processor_creator(**kwargs))

    destination = args.destination or config['stat']['destination']

    stat = TabunStat(
        source, destination, verbosity=args.verbosity,
        min_date=config['stat'].get('min_date'),
        max_date=config['stat'].get('max_date'),
        timezone=config['stat'].get('timezone'),
    )
    for p in processors:
        stat.add_processor(p)

    stat.go()

    stat.destroy()
    source.destroy()

    return 0


if __name__ == '__main__':
    sys.exit(main())
