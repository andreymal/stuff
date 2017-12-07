#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse

from . import diff


def dirdiff(
    input_dir1, input_dir2, output_dir, gzip_level=0,
    block_size_in=1024, block_size_out=1024 ** 2 * 32,
    mtime=True, modes=True, skip_del=False, hashsums=('sha256sum',), verbose=0
):
    '''Сохраняет разницу между файлами двух каталогов в третий каталог. Список
    файлов получает только из второго каталога; соответственно, удалённые
    файлы в патч не попадают. Сохраняет структуру каталогов. Симлинки
    переносит как есть. Метаданные каталогов и симлинков нигде не сохраняются;
    используйте какие-либо дополнительные средства их сохранения, если они вам
    нужны.

    :param input_dir1: путь к первому каталогу
    :param input_dir2: путь ко второму каталогу
    :param output_dir: путь к каталогу, куда будут записываться патчи
    :param int gzip_level: уровень gzip-сжатия для патчей
      (1-9, 0 — не сжимать, -1 — определить по расширению файла)
    :param int block_size_in: размер блоков, которые будут читаться
      и сравниваться (не может быть больше block_size_out)
    :param int block_size_out: максимальный размер блоков, которые будут
      записываться в патч (если 0, то неограниченно, но это может скушать
      оперативную память)
    :param bool mtime: если True, сохраняет даты изменения файлов в патч
    :param bool modes: если True, сохраняет POSIX права файлов в патч
    :param bool skip_del: если True, то в патч не будет записываться
      содержимое удалённых кусков файла. Так патч станет весить примерно
      в два раза меньше, но его нельзя будет откатить
    :param tuple hashsums: перечисление хэшей, которые нужно посчитать и
      записать в заголовки в файл патча; требуют поддержки seek и tell от fpp
    :param int verbose: если не ноль, то печатается прогресс в stderr
    '''

    # Нормализуем пути, чтоб имели одинаковый формат
    input_dir1 = os.path.join(os.path.abspath(input_dir1), '')  # ends with slash
    input_dir2 = os.path.join(os.path.abspath(input_dir2), '')
    output_dir = os.path.join(os.path.abspath(output_dir), '')

    for dirpath, dirs, files in os.walk(input_dir2):
        assert dirpath.startswith(input_dir2)  # /foo/bar/dirpath
        dirpath = dirpath[len(input_dir2):]  # dirpath

        for f in sorted(dirs + files):
            path_old = os.path.join(input_dir1, dirpath, f)
            path_new = os.path.join(input_dir2, dirpath, f)

            if not os.path.islink(path_new) and os.path.isdir(path_new):
                # Каталоги не-симлинки обработаются walk'ом
                continue

            if verbose - 1:
                print('Processing', os.path.join(dirpath, f), file=sys.stderr)
            elif verbose:
                print(os.path.join(dirpath, f), end='', file=sys.stderr)
                sys.stderr.flush()

            if os.path.islink(path_new):
                # Симлинки тупо копируем
                os.symlink(os.readlink(path_new), os.path.join(output_dir, dirpath, f))
                if verbose - 1:
                    print('Symlink was copied as is', file=sys.stderr)
                if verbose:
                    print('', file=sys.stderr)
                continue

            path_patch = os.path.join(output_dir, dirpath, f + '.abindiff')
            if gzip_level > 0:
                path_patch += '.gz'

            if not os.path.isdir(os.path.dirname(path_patch)):
                os.makedirs(os.path.dirname(path_patch))

            diff.create_bindiff_for_files(
                file1=path_old,
                file2=path_new,
                file_patch=path_patch,
                gzip_level=gzip_level,
                allow_empty=True,
                block_size_in=block_size_in,
                block_size_out=block_size_out,
                mtime=mtime,
                modes=modes,
                skip_del=skip_del,
                hashsums=hashsums,
                verbose=verbose - 1,
            )

            if verbose:
                print('', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Creates patchset between two directories (symlinks are copied as is)')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='"-v": print file names; "-vv": show progress')
    parser.add_argument('-M', '--nomtime', action='store_true', default=False, help='do not store modification date')
    parser.add_argument('-P', '--nomode', action='store_true', default=False, help='do not store POSIX file mode')
    parser.add_argument('-H', '--hash', default='sha256sum', help='calculate hashsums for old and new files (comma separated) (md5sum, sha1sum and/or sha256sum) (default: sha256sum)')
    parser.add_argument('-d', '--skip-del', action='store_true', default=False, help='do not store deleted blocks in patch (smaller, but this patch cannot be revertible)')
    parser.add_argument('-b', '--block-size', type=int, default=1024, help='block size in bytes (1 will generate byte-to-byte diff; default 1024)')
    parser.add_argument('-z', '--gzip', type=int, default=0, help='gzip compression level (1-9)')
    parser.add_argument('dir1', metavar='DIR1')
    parser.add_argument('dir2', metavar='DIR2')
    parser.add_argument('dirpatch', metavar='DIRPATCH')

    args = parser.parse_args()

    input_dir1 = os.path.join(os.path.abspath(args.dir1), '')  # ends with slash
    input_dir2 = os.path.join(os.path.abspath(args.dir2), '')
    output_dir = os.path.join(os.path.abspath(args.dirpatch), '')

    if len(set([
        os.path.abspath(x) for x in (input_dir1, input_dir2, output_dir)]
    )) != 3:
        print('Some directories are same, please check arguments', file=sys.stderr)
        return 1

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    elif os.listdir(output_dir):
        print('Output directory is not empty', file=sys.stderr)
        return 1

    dirdiff(
        input_dir1,
        input_dir2,
        output_dir,
        gzip_level=args.gzip,
        block_size_in=args.block_size,
        mtime=not args.nomtime,
        modes=not args.nomode,
        skip_del=args.skip_del,
        hashsums=[x.strip().lower() for x in args.hash.split(',') if x.strip()],
        verbose=args.verbose,
    )

    return 0


if __name__ == '__main__':
    sys.exit(main())
