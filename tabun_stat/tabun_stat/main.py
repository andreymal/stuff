#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse

import toml

from tabun_stat.stat import TabunStat
from tabun_stat import utils


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
    source = kwargs.pop('name')
    if source.startswith(':'):
        source = 'tabun_stat.datasource.' + source[1:]
    source = utils.import_string(source)
    source = source(**kwargs)

    processors = []
    for processor_data in config['processors']:
        kwargs = dict(processor_data)
        processor = kwargs.pop('name')
        if processor.startswith(':'):
            processor = 'tabun_stat.processors.' + processor[1:]
        processor = utils.import_string(processor)
        processors.append(processor(**kwargs))

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
