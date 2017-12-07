#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import gzip
import shutil
import argparse

from . import patch


def dirpatch(input_dir, output_dir, patch_dir, move=False, revert=False, check_hashsum=None, apply_meta=True, verbose=0):
    '''Ищет патчи в каталоге патчей, накладывает патчи на файлы из первого
    каталога и записывает результат файл во втором каталоге. Патчи должны
    иметь расширение ``.abindiff`` или ``.abindiff.gz``.

    Если указать первый и второй каталог одинаковыми, патчи будут применяться
    путём перезаписи соответствующих файлов (осторожно, можно случайно их
    угробить).

    Если в каталоге с патчами попадаются файлы без нужного расширения или
    симлинки, они просто копируются как есть.

    :param input_dir: путь к первому каталогу
    :param output_dir: путь ко второму каталогу
    :param patch_dir: путь к каталогу, откуда будут читаться патчи
    :param bool move: если True, файлы будут перемещаться из первого каталога
      во второй для ускорения и экономии место (непропатченные оригиналы
      при этом, естественно, потеряются)
    :param bool revert: если True, применяет патч наоборот (откатывает его);
      может вытать ошибку, если в патче отсутствуют удалённые куски и откат
      невозможен. Обратите внимание: так как adirdirr не делает патчей для
      удалённых файлов, их нельзя будет вернуть
    :param check_hashsum: если None, проверяет хэш-суммы файлов при наличии;
      если False, не проверяет; если True, проверяет всегда, а при отсутствии
      хэшей в патче кидает ошибку
    :param bool apply_meta: если True, применяет к пропатченному файлу
      мета-информацию (POSIX-права, дата изменения) при её наличии в патче
    :param int verbose: если не ноль, то печатается прогресс в stderr
    '''

    # Нормализуем пути, чтоб имели одинаковый формат
    input_dir = os.path.join(os.path.abspath(input_dir), '')  # ends with slash
    output_dir = os.path.join(os.path.abspath(output_dir), '')
    patch_dir = os.path.join(os.path.abspath(patch_dir), '')

    for dirpath, dirs, files in os.walk(patch_dir):
        assert dirpath.startswith(patch_dir)  # /foo/bar/dirpath
        dirpath = dirpath[len(patch_dir):]  # dirpath

        for f in sorted(dirs + files):
            path_old = os.path.join(input_dir, dirpath, f)  # путь к старому файлу (читаем)
            path_new = os.path.join(output_dir, dirpath, f)  # путь к новому файлу (пишем)
            path_patch = os.path.join(patch_dir, dirpath, f)  # файл в каталоге патчей (собственно патч, файл-не-патч или симлинк)

            if not os.path.islink(path_patch) and os.path.isdir(path_patch):
                # Каталоги не-симлинки обработаются walk'ом
                continue

            if verbose:
                print(os.path.join(dirpath, f), end='', file=sys.stderr)
                sys.stderr.flush()

            if os.path.islink(path_patch):
                # Симлинки тупо копируем
                if path_old != path_new:
                    os.symlink(os.readlink(path_patch), path_new)
                if verbose:
                    print('', file=sys.stderr)
                continue

            if not f.lower().endswith('.abindiff') and not f.lower().endswith('.abindiff.gz'):
                # Файлы, которые не патчи, тоже тупо копируем
                if path_old != path_new:
                    shutil.copy2(path_patch, path_new)
                if verbose:
                    print('', file=sys.stderr)
                continue

            # У путей к реальным файлам откусываем расширение патча
            if f.lower().endswith('.abindiff.gz'):
                path_old = path_old[:-12]
                path_new = path_new[:-12]
            else:
                path_old = path_old[:-9]
                path_new = path_new[:-9]

            if not os.path.isdir(os.path.dirname(path_new)):
                os.makedirs(os.path.dirname(path_new))

            # Если нас просят перемещать, перемещаем
            if move and path_old != path_new:
                if os.path.exists(path_old):
                    os.rename(path_old, path_new)
                path_old = path_new

            if not move and path_old == path_new:
                raise ValueError('Same input and output path are not allowed without move option')

            if move and not os.path.exists(path_new):
                with open(path_new, 'wb'):
                    pass  # touch

            patch.apply_patch_for_files(
                file_input=path_old,
                file_output=path_new,
                file_patch=path_patch,
                allow_empty=True,
                revert=revert,
                check_hashsum=check_hashsum,
                apply_meta=apply_meta,
            )

            # Откат свежесозданного файла означает его удаление
            if revert and os.stat(path_new).st_size == 0:
                if path_patch.lower().endswith('.gz'):
                    fpp = gzip.open(path_patch, 'rb')
                else:
                    fpp = open(path_patch, 'rb')
                with fpp:
                    headers = patch.read_headers(fpp)
                if headers.get('1-mtime') == '1970-01-01T00:00:00.000000Z' and headers.get('1-mode') == '---------':
                    os.remove(path_new)

            if verbose:
                print('', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Applies patchset to directory')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='show file names in progress')
    parser.add_argument('-m', '--move', action='store_true', default=False, help='Move files from input to output before patch (be careful!)')
    parser.add_argument('-R', '--revert', '--reverse', action='store_true', default=False, help='revert patch')
    parser.add_argument('-H', '--nohash', action='store_true', default=False, help='do not check hashsums')
    parser.add_argument('-M', '--nometa', action='store_true', default=False, help='do not apply meta information (mtime and POSIX file mode)')
    parser.add_argument('-e', '--allow-empty', action='store_true', default=False, help='interpret non-existing input files as empty files')
    parser.add_argument('dirpatch', metavar='PATCHDIR')
    parser.add_argument('dir1', metavar='INPUTDIR')
    parser.add_argument('dir2', metavar='OUTPUTDIR', nargs='?')

    args = parser.parse_args()

    input_dir = os.path.join(os.path.abspath(args.dir1), '')  # ends with slash
    output_dir = os.path.join(os.path.abspath(args.dir2 or args.dir1), '')
    patch_dir = os.path.join(os.path.abspath(args.dirpatch), '')

    if args.move and (input_dir == patch_dir or output_dir == patch_dir):
        print('Some directories are same with patch directory, please check arguments', file=sys.stderr)
        return 1

    if not args.move and len(set([
        os.path.abspath(x) for x in (input_dir, output_dir, patch_dir)]
    )) != 3:
        print('Some directories are same, please check arguments', file=sys.stderr)
        return 1

    if input_dir != output_dir:
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        elif os.listdir(output_dir):
            print('Output directory is not empty', file=sys.stderr)
            return 1

    dirpatch(
        input_dir,
        output_dir,
        patch_dir,
        move=args.move,
        revert=args.revert,
        check_hashsum=False if args.nohash else None,
        apply_meta=not args.nometa,
        verbose=args.verbose,
    )

    return 0


if __name__ == '__main__':
    sys.exit(main())
