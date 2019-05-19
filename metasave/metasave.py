#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import stat
import hashlib
import argparse
from datetime import datetime
from typing import Any, Optional, Iterable, List, Dict, Set, TextIO

try:
    import pwd
    import grp
except ImportError:  # Windows
    pwd = None
    grp = None


use_stdout = None  # type: Optional[bool]
out_fp = None  # type: Optional[TextIO]
je = None  # type: Optional[json.JSONEncoder]


class MetaSaveError(Exception):
    pass


class MetaSave:
    def __init__(
        self,
        paths: Iterable[str],
        root: Optional[str] = None,
        hashers: Optional[Dict[str, Any]] = None,
        ignore_paths: Optional[Iterable[str]] = None,
        skip: Optional[Iterable[str]] = None,
    ):
        """
        :param list paths: список обрабатываемых путей (файлы или каталоги)
        :param str root: каталог, относительно которого будут считаться пути
          (если не указано, будут использоваться абсолютные пути)
        :param dict hashers: словарь {'название_хэша': HasherClass}
          с алгоритмами хэширования, которые будут подсчитываться для каждого
          файла; класс должен поддерживать методы update и hexdigest
        :param list ignore_paths: список игнорируемых путей (относительно root
          или абсолютные)
        :param set skip: список названий ключей, которые следует не добавлять
          в результат (ctime, mtime, mode, uid, user, gid, group)
        """

        if isinstance(paths, str):
            self._paths = [paths]
        else:
            self._paths = list(paths)

        self._root = os.path.abspath(root) if root else None  # type: Optional[str]
        self._hashers = dict(hashers or {})  # type: Dict[str, Any]
        self._ignore_paths = set()  # type: Set[str]
        for x in ignore_paths or ():
            self._ignore_paths.add(os.path.abspath(os.path.join(self._root or '.', x)))
        self._skip = set(skip or ())  # type: Set[str]

        self._queue = self._collect_queue()  # type: List[str]

    def get_queue(self) -> List[str]:
        """Возвращает копию очереди."""
        return self._queue[:]

    def get_next_path(self) -> Optional[str]:
        """Возвращает следующий путь из очереди. Если очередь пуста, то
        возвращает None.
        """
        if not self._queue:
            return None
        return self._queue[-1]

    def pop_next_path(self) -> Optional[str]:
        """Возвращает следующий путь из очереди, при этом удаляя его из этой
        самой очереди. Если очередь пуста, то возвращает None.
        """
        if not self._queue:
            return None
        return self._queue.pop()

    def next(self) -> Optional[Dict[str, Any]]:
        """Считает мету для следующего пути в очереди. Если очередь пуста,
        то возвращает None. Если путь является каталогом, добавляет лежащие
        в нём файлы и подкаталоги в очередь. Если случается ошибка,
        то исключение выбрасывается без удаления пути из очереди; чтобы
        пропустить проблемый путь, используйте pop_next_path.
        """
        path = self.get_next_path()
        if path is None:
            return None
        meta = self.calc_meta(path)

        queue_ext = []  # type: List[str]
        for p in meta.pop('contents', []):
            p_abs = os.path.abspath(os.path.join(self._root or '.', p))
            if p_abs in self._ignore_paths:
                continue
            queue_ext.append(p)
        queue_ext.sort(reverse=True)

        self.pop_next_path()
        self._queue.extend(queue_ext)

        return {
            'path': path,
            'meta': meta,
        }

    def calc_meta(self, path: str) -> Dict[str, Any]:
        """Считает мету для указанного пути."""
        if self._root:
            abspath = os.path.abspath(os.path.join(self._root, path))
        else:
            abspath = path
            if abspath != os.path.abspath(path):
                raise ValueError('Path must be absolute')

        if os.path.islink(abspath):
            return {
                'type': 'symlink',
                'to': os.readlink(abspath).replace(os.path.sep, '/'),
            }

        path_stat = os.stat(abspath)

        meta = {}  # type: Dict[str, Any]

        if os.path.isdir(abspath):
            # Если есть root и path относительный, то сохраняем
            # относительность и в contents тоже (и слэши прямые, да)
            meta = {
                'type': 'directory',
                'contents': [path + '/' + x for x in os.listdir(abspath)],
            }

        elif os.path.isfile(abspath):
            meta = {
                'type': 'file',
                'size': path_stat.st_size,
            }

            file_hashers = {}  # type: Dict[str, Any]
            for hash_name, hasher_class in self._hashers.items():
                file_hashers[hash_name] = hasher_class()

            if file_hashers:
                with open(abspath, 'rb') as fp:
                    while True:
                        chunk = fp.read(16384)
                        if not chunk:
                            break
                        for hasher in file_hashers.values():
                            hasher.update(chunk)

                for hash_name, hasher in file_hashers.items():
                    meta[hash_name] = hasher.hexdigest()

        elif stat.S_ISFIFO(path_stat.st_mode):
            meta = {
                'type': 'fifo',
            }

        elif stat.S_ISSOCK(path_stat.st_mode):
            meta = {
                'type': 'sock',
            }

        elif stat.S_ISBLK(path_stat.st_mode):
            meta = {
                'type': 'blk',
            }

        elif stat.S_ISCHR(path_stat.st_mode):
            meta = {
                'type': 'chr',
            }

        else:
            raise MetaSaveError('Unsupported file type {!r}'.format(abspath))

        if 'uid' not in self._skip:
            meta['uid'] = path_stat.st_uid
        if 'user' not in self._skip:
            try:
                meta['user'] = pwd.getpwuid(path_stat.st_uid)[0] if pwd else None
            except KeyError:
                meta['user'] = None
        if 'gid' not in self._skip:
            meta['gid'] = path_stat.st_gid
        if 'group' not in self._skip:
            try:
                meta['group'] = grp.getgrgid(path_stat.st_gid)[0] if grp else None
            except KeyError:
                meta['group'] = None
        if 'mode' not in self._skip:
            meta['mode'] = stat.filemode(path_stat.st_mode)[1:]
        if 'ctime' not in self._skip:
            meta['ctime'] = datetime.utcfromtimestamp(path_stat.st_ctime).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if 'mtime' not in self._skip:
            meta['mtime'] = datetime.utcfromtimestamp(path_stat.st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        return meta

    # helpers

    def _collect_queue(self) -> List[str]:
        """Собирает пользовательский список путей в заготовку для очереди.
        Все пути формируются относительно root (если он не указан,
        используются абсолютные пути). Все пути используют прямой слэш,
        даже на Windows.
        """

        prefix = os.path.join(self._root, '') if self._root is not None else None  # type: Optional[str]
        queue = set()  # type: Set[str]

        for x in self._paths:
            path = os.path.abspath(x)
            # Сам root обозначаем просто точкой
            if path == self._root:
                queue.add('.')
                continue

            # Если указан root, то все пути должны лежать внутри него
            if prefix is not None and not path.startswith(prefix):
                raise MetaSaveError('{!r} is not in root directory {!r}'.format(path, prefix))

            if not os.path.exists(path):
                raise MetaSaveError('{!r} is not found'.format(path))

            # Добавляем в очередь путь относительно root и без слэшей в конце
            relpath = ('./' + path[len(prefix):]) if prefix is not None else path
            queue.add(relpath.replace(os.path.sep, '/').rstrip('/'))

        # TODO: убрать вложенки (случаи вида queue = {'/a/b', '/a/b/c'})

        # Сортируем в обратном порядке: последние элементы обрабатываются первыми
        queue_list = sorted(queue, reverse=True)
        return queue_list


def fprint(*args: Any, **kwargs: Any) -> None:
    assert 'file' not in kwargs
    assert 'flush' not in kwargs
    if use_stdout:
        print(*args, **kwargs, flush=True)
    if out_fp:
        kwargs['file'] = out_fp
        print(*args, **kwargs)


def indent_json(data: Dict[str, Any], indent: int = 2, keep_first_line: bool = False) -> str:
    assert je is not None
    if not isinstance(data, dict):
        raise ValueError
    result = je.encode(data)[1:-1].rstrip('\n')
    result = result.replace('\n', '\n' + (' ' * indent)).lstrip('\n')
    if keep_first_line:
        result = (' ' * indent) + result
    return result


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


# main


def main() -> int:
    global use_stdout, out_fp, je

    parser = argparse.ArgumentParser(description='Calculates meta information for directories, files and symlinks.')
    parser.add_argument('-o', '--output', help='path to output file (default stdout)')
    parser.add_argument('-A', '--absolute', action='store_true', help='use absolute paths')
    parser.add_argument('-v', '--verbose', action='store_true', help='show progress and statistics in stderr')
    parser.add_argument('--jsonl', action='store_true', help='use JSON Lines format insted of single JSON object')
    parser.add_argument('--skip', action='append', help='do not add some fields (ctime, mtime, mode, uid, user, gid, group)')
    parser.add_argument('-I', '--ignore-path', action='append', help='do not process these paths (absolute or relative to current directory)')
    parser.add_argument('--stdout', action='store_true', help='duplicate output to stdout even if file is set')
    parser.add_argument('-a', '--append', action='store_true', help='append data to existing file')
    parser.add_argument('-w', '--overwrite', action='store_true', help='remove data from existing file and write only new data')
    parser.add_argument('-E', '--ignore-errors', action='store_true', help='ignore I/O and unicode errors')
    parser.add_argument('--md5sum', action='store_true', help='calculate MD5 hashsum for files')
    parser.add_argument('--sha1sum', action='store_true', help='calculate SHA1 hashsum for files')
    parser.add_argument('--no-sha256sum', action='store_true', help='do not calculate SHA256 hashsum for files (calculated by default)')
    parser.add_argument('paths', metavar='PATH', nargs='+', help='files or directories for processing')

    args = parser.parse_args()

    # Проверяем адекватность аргументов
    output_path = args.output  # type: str
    if output_path:
        output_path = os.path.abspath(output_path)
        if os.path.exists(output_path):
            if args.append == args.overwrite:
                print('Output path already exists! Please set "-a" or "-w" option.', file=sys.stderr)
                return 2

    # Собираем классы для хэширования
    hashers = {}  # type: Dict[str, Any]
    if args.md5sum:
        hashers['md5sum'] = hashlib.md5
    if args.sha1sum:
        hashers['sha1sum'] = hashlib.sha1
    if not args.no_sha256sum:
        hashers['sha256sum'] = hashlib.sha256

    use_stdout = bool(not output_path or args.stdout)
    verbose = args.verbose  # type: bool
    jsonl = args.jsonl  # type: bool
    ignore_errors = args.ignore_errors  # type: bool
    root = None if args.absolute else os.path.abspath('.')  # type: Optional[str]

    # Собираем все skip'ы в единое множество
    skip = set()  # type: Set[str]
    for s in (args.skip or ()):
        for x in s.split(','):
            x = x.strip().lower()
            if x:
                skip.add(x)

    # Обрабатываем игнорируемые пути
    ignore_paths = set()  # type: Set[str]
    for x in args.ignore or []:
        x = os.path.abspath(os.path.join(root or '.', x))
        if not os.path.exists(x):
            # Спасаем пользователя от возможных опечаток
            print('WARNING: ignored path {!r} not found'.format(x), file=sys.stderr)
        ignore_paths.add(x)

    # Если указан output, то его тоже следует игнорировать
    if output_path:
        ignore_paths.add(output_path)

    ms = MetaSave(
        paths=args.paths,
        root=root,
        hashers=hashers,
        ignore_paths=ignore_paths,
        skip=skip,
    )

    old_meta = {}  # type: Dict[str, Any]
    out_fp = None
    if output_path:
        if args.append:
            try:
                with open(output_path, 'r', encoding='utf-8-sig') as fp:
                    if not jsonl:
                        old_meta = json.load(fp)
                    else:
                        for line in fp:
                            data = json.loads(line)
                            old_meta[data['path']] = data['meta']
            except FileNotFoundError:
                pass

        out_fp = open(output_path, 'w', encoding='utf-8')

    if jsonl:
        je = json.JSONEncoder(ensure_ascii=False, sort_keys=True)
    else:
        je = json.JSONEncoder(ensure_ascii=False, sort_keys=True, indent=2)

    # Собираем статистику для красоты verbose
    files_count = 0
    directories_count = 0
    symlinks_count = 0
    size_sum = 0
    errors = 0

    # Если не jsonl, то форматом вывода является единый JSON-объект
    if not jsonl:
        fprint('{')

    try:
        first = True
        while True:
            # Достаём следующий путь из очереди и печатаем заголовок
            path = ms.get_next_path()
            if path is None:
                break

            if verbose:
                print('[{}] {}'.format(
                    files_count + directories_count + symlinks_count + errors + 1,
                    path,
                ), end='', file=sys.stderr, flush=True)

            try:
                meta = ms.next()
            except OSError as exc:
                if not ignore_errors:
                    raise
                if verbose:
                    print(' ', end='', file=sys.stderr)
                print('Cannot calculate meta for {!r}: {}: {}'.format(
                    path,
                    type(exc).__name__,
                    str(exc),
                ), file=sys.stderr, flush=True)
                ms.pop_next_path()
                errors += 1
                if out_fp:
                    out_fp.flush()
                continue

            assert meta is not None  # Потому что выше уже path проверили
            assert meta['path'] == path

            json_path = je.encode(path)
            json_meta = je.encode(meta['meta']) if jsonl else indent_json(meta['meta'])

            # Костыль для игнора ошибки UnicodeEncodeError surrogates not allowed
            if ignore_errors:
                try:
                    json_path.encode('utf-8')
                    json_meta.encode('utf-8')
                except Exception as exc:
                    if verbose:
                        print(' ', end='', file=sys.stderr)
                    print('Cannot encode meta for {!r}: {}: {}'.format(
                        path,
                        type(exc).__name__,
                        str(exc),
                    ), file=sys.stderr, flush=True)
                    errors += 1
                    if out_fp:
                        out_fp.flush()
                    continue

            if meta['meta']['type'] == 'symlink':
                symlinks_count += 1
            elif meta['meta']['type'] == 'directory':
                directories_count += 1
            else:
                files_count += 1
                size_sum += int(meta['meta'].get('size', 0))

            # Если путь уже был в старом файле, то мету обновляем
            old_meta.pop(path, None)

            if not jsonl:
                if not first:
                    fprint('  },')
                fprint('  {0}: {{\n{1}'.format(
                    json_path,
                    json_meta,
                ))

            else:
                # Делаем так, чтобы JSONEncoder не отсортировал и path был
                # на первом месте — так красивее и удобнее
                fprint('{{"path": {}, "meta": {}}}'.format(
                    json_path,
                    json_meta,
                ))

            first = False

            if verbose:
                print('', file=sys.stderr, flush=True)

        # Если остались старые данные из старого файла, дописываем их в конец
        # (если старый файл был отсортирован, то и тут отсортируется как надо)
        # (вырожденный случай: ./metasave.py -a -o meta.json meta.json перезапишет файл, не изменив ни байта)
        for k, meta1 in sorted(old_meta.items(), key=lambda x: x[0].split('/')):
            if not isinstance(meta1, dict):
                raise ValueError("Old meta file has unexpected non-dict data")
            if not jsonl:
                if not first:
                    fprint('  },')
                first = False
                fprint('  {}: {{'.format(je.encode(k)))
                fprint(indent_json(meta1))
            else:
                fprint('{{"path": {}, "meta": {}}}'.format(
                    je.encode(k),
                    je.encode(meta1),
                ))

        if not jsonl:
            if not first:
                fprint('  }')
            fprint('}')

        if verbose:
            print('{0} ({1} files, {2} directories, {3} symlinks, {4} errors)'.format(
                human_size(size_sum),
                files_count,
                directories_count,
                symlinks_count,
                errors,
            ), file=sys.stderr)

    except (KeyboardInterrupt, SystemExit):
        if not jsonl:
            if not first:
                fprint('  }')
            fprint('}')

        if verbose:
            print('', file=sys.stderr)
            print('Interrupted', file=sys.stderr)

    finally:
        if out_fp is not None:
            out_fp.close()
            out_fp = None

    return 0


if __name__ == '__main__':
    sys.exit(main())
