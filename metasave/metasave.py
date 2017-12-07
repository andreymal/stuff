#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import stat
import hashlib
import argparse
from datetime import datetime


je = json.JSONEncoder(ensure_ascii=False, sort_keys=True, indent=2)

hashes = {}
use_stdout = None
out_fp = None


# worker


def calc_dir_meta(path, noctime=False):
    path_stat = os.stat(path)

    meta = {
        'type': 'directory',
        'mode': stat.filemode(path_stat.st_mode)[1:],
        'ctime': datetime.utcfromtimestamp(path_stat.st_ctime).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'mtime': datetime.utcfromtimestamp(path_stat.st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
    }

    if noctime:
        del meta['ctime']

    return meta


def calc_link_meta(path):
    meta = {
        'type': 'symlink',
        'to': os.readlink(path),
    }

    return meta


def calc_file_meta(path, noctime=False):
    path_stat = os.stat(path)

    hash_results = {}
    if hashes:
        for k, hasher_func in hashes.items():
            hash_results[k] = hasher_func()

        with open(path, 'rb') as fp:
            while True:
                chunk = fp.read(16384)
                if not chunk:
                    break
                for hasher in hash_results.values():
                    hasher.update(chunk)

    meta = {
        'type': 'file',
        'mode': stat.filemode(path_stat.st_mode)[1:],
        'ctime': datetime.utcfromtimestamp(path_stat.st_ctime).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'mtime': datetime.utcfromtimestamp(path_stat.st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'size': path_stat.st_size,
    }
    for k, hasher in hash_results.items():
        meta[k] = hasher.hexdigest()

    if noctime:
        del meta['ctime']

    return meta


# utils


def collect_queue(paths):
    '''Подготавливает изначальный стек обрабатываемых путей, проверяя пути
    из аргументов командной строки.
    '''

    curdir = os.path.abspath('.')
    prefix = os.path.join(curdir, '')  # adds os.path.sep
    queue = set()
    for x in paths:
        path = os.path.abspath(x)
        if path == curdir:
            queue.add('.')
            continue

        if not path.startswith(prefix):
            print('{!r} is not in current directory'.format(path), file=sys.stderr)
            return None
        if not os.path.exists(path):
            print('{!r} is not found'.format(path), file=sys.stderr)
            return None
        queue.add('./' + path[len(prefix):].replace(os.path.sep, '/').rstrip('/'))

    queue = list(sorted(queue, reverse=True))
    return queue


def fprint(*args, **kwargs):
    assert 'file' not in kwargs
    if use_stdout:
        print(*args, **kwargs)
        sys.stdout.flush()
    if out_fp:
        kwargs['file'] = out_fp
        print(*args, **kwargs)
        out_fp.flush()


def indent_json(data, indent=2, keep_first_line=False):
    result = je.encode(data)[1:-1].rstrip('\n').replace('\n', '\n' + (' ' * indent)).lstrip('\n')
    if keep_first_line:
        result = (' ' * indent) + result
    return result


# main


def main():
    global use_stdout, out_fp

    parser = argparse.ArgumentParser(description='Calculates meta information for directories, files and symlinks.')
    parser.add_argument('-o', '--output', help='path to output file (default stdout)')
    parser.add_argument('-v', '--verbose', action='store_true', help='show progress in stderr')
    parser.add_argument('-C', '--noctime', action='store_true', help='do not add file creation time to output')
    parser.add_argument('--stdout', action='store_true', help='duplicate output to stdout even if file is set')
    parser.add_argument('-a', '--append', action='store_true', help='append data to existing file')
    parser.add_argument('-w', '--overwrite', action='store_true', help='remove data from existing file and write only new data')
    parser.add_argument('--md5sum', action='store_true', help='calculate MD5 hashsum for files')
    parser.add_argument('--sha1sum', action='store_true', help='calculate SHA1 hashsum for files')
    parser.add_argument('--no-sha256sum', action='store_true', help='do not calculate SHA256 hashsum for files (calculated by default)')
    parser.add_argument('paths', metavar='PATH', nargs='+', help='files or directories for processing')

    args = parser.parse_args()

    # Проверяем адекватность аргументов
    output_path = args.output
    if output_path:
        output_path = os.path.abspath(output_path)
        if os.path.exists(output_path):
            if args.append == args.overwrite:
                print('Output path already exists! Please set "-a" or "-w" option.', file=sys.stderr)
                return 2

    if args.md5sum:
        hashes['md5sum'] = hashlib.md5
    if args.sha1sum:
        hashes['sha1sum'] = hashlib.sha1
    if not args.no_sha256sum:
        hashes['sha256sum'] = hashlib.sha256

    use_stdout = not output_path or args.stdout
    verbose = args.verbose
    noctime = args.noctime

    # Собираем и нормализуем пути для обработки. Все должны быть в текущем
    # каталоге, без слэшей по краям и начинаться с ./
    queue = collect_queue(args.paths)
    if queue is None:
        return 1

    old_meta = {}
    out_fp = None
    if output_path:
        if args.append:
            with open(output_path, 'r', encoding='utf-8-sig') as fp:
                old_meta = json.load(fp)

        out_fp = open(output_path, 'w', encoding='utf-8')

    try:
        fprint('{')

        first = True
        while queue:
            # Достаём следующий путь из очереди и печатаем заголовок
            path = queue.pop()
            if output_path and os.path.abspath(path) == output_path:
                continue

            if first:
                first = False
            else:
                fprint('  },')

            if verbose:
                print(path, end='', file=sys.stderr)
                sys.stderr.flush()

            fprint('  {}: {{'.format(je.encode(path)))

            # Если путь уже был в старом файле, то мету обновляем
            old_meta.pop(path, None)

            # Считаем мету в зависимости от типа файла
            if os.path.isdir(path):
                meta = calc_dir_meta(path, noctime=noctime)
                dirpaths = os.listdir(path)
                dirpaths.sort(reverse=True)
                queue.extend([path + '/' + x for x in dirpaths])
            elif os.path.islink(path):
                meta = calc_link_meta(path)
            elif os.path.isfile(path):
                meta = calc_file_meta(path, noctime=noctime)
            else:
                raise ValueError('Unsupported file type {!r}'.format(path))

            # И печатаем её
            fprint(indent_json(meta))

            if verbose:
                print('', file=sys.stderr)

        # Если остались старые данные из старого файла, дописываем их в конец
        # (если старый файл был отсортирован, то и тут отсортируется как надо)
        # (вырожденный случай: ./metasave.py -a -o meta.json meta.json перезапишет файл, не изменив ни байта)
        for k, meta in sorted(old_meta.items(), key=lambda x: x[0].split(os.path.sep)):
            if not first:
                fprint('  },')
            first = False
            fprint('  {}: {{'.format(je.encode(k)))
            fprint(indent_json(meta))

        if not first:
            fprint('  }')

        fprint('}')
    finally:
        if out_fp:
            out_fp.close()
            out_fp = None

    return 0


if __name__ == '__main__':
    sys.exit(main())
