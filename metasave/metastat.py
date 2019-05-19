#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import argparse
from typing import Any, Optional, Iterable, List, Dict, Set


class MetaStat:
    def __init__(self, uniq_key: str, ignore_keys: Optional[Iterable[str]] = None):
        self._uniq_key = uniq_key
        self._files = {}  # type: Dict[str, List[str]]
        self._sizes = {}  # type: Dict[str, int]
        self._ignore_keys = set(ignore_keys or ())  # type: Set[str]

    def read_file(self, p: str) -> None:
        with open(p, 'r', encoding='utf-8-sig') as fp:
            line = fp.readline().strip()
            jsonl = True
            try:
                json.loads(line)
            except Exception:
                jsonl = False

            fp.seek(0, 0)

            if jsonl:
                for line in fp:
                    self.read_meta(json.loads(line))
            else:
                data = json.load(fp)  # type: Dict[str, Any]
                if not isinstance(data, dict):
                    raise ValueError
                for path, meta in data.items():
                    self.read_meta({'path': path, 'meta': meta})

    def read_meta(self, data: Dict[str, Any]) -> None:
        path = data['path']  # type: str
        meta = data['meta']  # type: Dict[str, Any]

        if meta.get('type') != 'file':
            return

        try:
            key = meta[self._uniq_key]
            if not key:
                raise ValueError
        except Exception:
            raise ValueError('Cannot get key {!r} for file {!r}'.format(self._uniq_key, path))

        if key in self._ignore_keys:
            return

        if key not in self._files:
            self._files[key] = []
            self._sizes[key] = meta['size']

        self._files[key].append(path)

    def calculate_duplicates(self, min_count: int = 2, min_size: int = 10485760) -> List[Dict[str, Any]]:
        data = [
            {'size': self._sizes[x[0]], 'key': x[0], 'paths': x[1]}
            for x in self._files.items()
            if len(x[1]) >= min_count and self._sizes[x[0]] >= min_size
        ]  # type: List[Dict[str, Any]]

        data.sort(key=lambda x: x['size'] * len(x['paths']), reverse=True)
        return data

    def write_duplicates_to_file(self, path: str) -> None:
        data = self.calculate_duplicates()

        dup_size = sum(x['size'] * len(x['paths']) for x in data)  # type: int
        nodup_size = sum(x['size'] * 1 for x in data)  # type: int

        with open(path, 'w', encoding='utf-8') as fp:
            fp.write('Size with duplicates: {0}\n'.format(human_size(dup_size)))
            fp.write('Unique size: {0}\n'.format(human_size(nodup_size)))

            for x in data:
                fp.write('\n')

                fp.write('{0} x {1}  {2}:\n'.format(
                    human_size(x['size']),
                    len(x['paths']),
                    x['key'],
                ))
                for p in x['paths']:
                    fp.write('  {}\n'.format(p))

    def calculate_biggest(self, min_size: int = 10485760) -> List[Dict[str, Any]]:
        data = [
            {'size': self._sizes[x[0]], 'key': x[0], 'paths': x[1]}
            for x in self._files.items()
            if self._sizes[x[0]] >= min_size
        ]  # type: List[Dict[str, Any]]

        data.sort(key=lambda x: x['size'], reverse=True)
        return data

    def write_biggest_to_file(self, path: str) -> None:
        data = self.calculate_biggest()

        with open(path, 'w', encoding='utf-8') as fp:
            first = True

            for x in data:
                if first:
                    first = False
                else:
                    fp.write('\n')

                fp.write('{0} x {1}  {2}:\n'.format(
                    human_size(x['size']),
                    len(x['paths']),
                    x['key'],
                ))
                for p in x['paths']:
                    fp.write('  {}\n'.format(p))

    def calculate_summary(self) -> Dict[str, Any]:
        return {
            'all_uniq_size': sum(self._sizes.values()),
            'all_size': sum(self._sizes[x[0]] * len(x[1]) for x in self._files.items()),
            'all_uniq_count': len(self._files),
            'all_count': sum(len(x) for x in self._files.values()),
        }


def human_size(n: int) -> str:
    if n == 1:
        return '1 byte'
    if n <= 10 ** 3:
        return '{} bytes'.format(n)
    if n <= 10 ** 6:
        return '{:.2f} KiB'.format(n / 1024.0)
    if n <= 10 ** 9:
        return '{:.2f} MiB'.format(n / 1024.0 ** 2)
    if n <= 10 ** 12:
        return '{:.2f} GiB'.format(n / 1024.0 ** 3)
    return '{:.2f} TiB'.format(n / 1024.0 ** 4)


def main() -> int:
    parser = argparse.ArgumentParser(description='Calculates some stat using meta information.')
    parser.add_argument('--dup', help='path to output information about duplicates')
    parser.add_argument('--big', help='path to output information about biggest files')
    parser.add_argument('--ignore-key', action='append', help='do not process these files')
    parser.add_argument('-v', '--verbose', action='store_true', help='show progress and statistics in stderr')
    parser.add_argument('--key', default='sha256sum', help='meta key that will be used as unique key (default: sha256sum)')
    parser.add_argument('paths', metavar='PATH', nargs='+', help='json or jsonl files that were generated by metasave.py')

    args = parser.parse_args()

    ms = MetaStat(args.key, ignore_keys=args.ignore_key)
    for p in args.paths:
        if args.verbose:
            print('Reading {!r}...'.format(p), file=sys.stderr)
        ms.read_file(p)

    if args.dup:
        if args.verbose:
            print('Writing duplicates to {!r}...'.format(args.dup), file=sys.stderr)
        ms.write_duplicates_to_file(args.dup)

    if args.big:
        if args.verbose:
            print('Writing biggest files to {!r}...'.format(args.big), file=sys.stderr)
        ms.write_biggest_to_file(args.big)

    if args.verbose:
        print('Calculate summary...', file=sys.stderr)
    summary = ms.calculate_summary()

    print('Full size: {0} ({1} files)'.format(human_size(summary['all_size']), summary['all_count']))
    print('Unique size: {0} ({1} files)'.format(human_size(summary['all_uniq_size']), summary['all_uniq_count']))

    return 0


if __name__ == '__main__':
    sys.exit(main())
