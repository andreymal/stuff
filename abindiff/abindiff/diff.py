#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import gzip
import stat
import time
import hashlib
import argparse
from datetime import datetime


def _bindiff(fp1, fp2, block_size_in=1024):
    '''Поблочно читает два файловых объекта и для каждого блока возвращает
    кортеж из трёх элементов:

    - ``=``  или ``!`` — совпадают ли блоки
    - блок из первого файла
    - блок из второго файла

    Если один из блоков пустой, значит соответствующий файл кончился.

    :param fp1: первый файл (file-подобный объект)
    :param fp2: второй файл (file-подобный объект)
    :param int block_size_in: размер блоков, которые будут читаться
      и сравниваться
    '''

    while True:
        block1 = fp1.read(block_size_in)
        block2 = fp2.read(block_size_in)
        if not block1 and not block2:
            return

        if block1 == block2:
            yield '=', block1, block2
        else:
            yield '!', block1, block2


def _flush_buf(fpp, last_act, last_data1, last_data2, skip_del=False):
    data1 = b''.join(last_data1)
    data2 = b''.join(last_data2)
    last_data1.clear()
    last_data2.clear()

    b = 0

    if last_act == '=':
        assert data1 == data2
        if data1:
            b += fpp.write('= {}\n\n'.format(len(data1)).encode('utf-8'))

    elif last_act == '!':
        if data1 and data2:
            assert data1 != data2

        if data1:
            if not skip_del:
                b += fpp.write('- {}\n\n'.format(len(data1)).encode('utf-8'))
                b += fpp.write(data1)
                b += fpp.write(b'\n\n')
            else:
                b += fpp.write('- {} skip=1\n\n'.format(len(data1)).encode('utf-8'))

        if data2:
            b += fpp.write('+ {}\n\n'.format(len(data2)).encode('utf-8'))
            b += fpp.write(data2)
            b += fpp.write(b'\n\n')

    return b


def create_bindiff(
    fp1, fp2, fpp, block_size_in=1024, block_size_out=1024 ** 2 * 32,
    file_size=None, skip_del=False, meta=None, hashsums=('sha256sum',), verbose=0
):
    '''Поблочно считает разницу между двумя файлами и записывает патч
    в третий файл. Возвращает словарь со всякой разной статистикой.

    :param fp1: первый файл (file-подобный объект)
    :param fp2: второй файл (file-подобный объект)
    :param fpp: файл, куда будет записываться патч (file-подобный объект;
      при указанных хэшах требуется поддержка seek и tell)
    :param int block_size_in: размер блоков, которые будут читаться
      и сравниваться (не может быть больше block_size_out)
    :param int block_size_out: максимальный размер блоков, которые будут
      записываться в патч (если 0, то неограниченно, но это может скушать
      оперативную память)
    :param int file_size: максимальный размер одного из двух файлов,
      используется с verbose для печати прогресса в консоль
    :param bool skip_del: если True, то в патч не будет записываться
      содержимое удалённых кусков файла. Так патч станет весить примерно
      в два раза меньше, но его нельзя будет откатить
    :param dict meta: словарь с заголовками, которые будут записаны в начале
      патча перед самими блоками с разницей
    :param tuple hashsums: перечисление хэшей, которые нужно посчитать и
      записать в заголовки в файл патча; требуют поддержки seek и tell от fpp
    :param int verbose: если не ноль, то печатается прогресс в stderr
    '''

    changed_cnt = 0
    all_cnt = 0
    bytes_processed = 0
    patch_size = 0

    # Готовимся считать хэши
    hashers_old = create_hashers(hashsums)
    hashers_new = create_hashers(hashsums)

    # Пишем заголовок патча
    patch_size += fpp.write(b'abindiff 001\n')

    if verbose:
        vprint(changed_cnt, all_cnt, bytes_processed, file_size)
    tm = time.time()

    # После заголовка пишем всякую разную мету
    if meta:
        for k, v in meta.items():
            patch_size += fpp.write('{}: {}\n'.format(k.lower(), v).encode('utf-8'))


    # Хэши считаются в процессе записи патча, поэтому резервируем место
    # в заголовках; после завершения мы вернёмся сюда с помощью seek и запишем
    # посчитанные хэши (поэтому с gzip это не работает и хэши нужно считать
    # заранее)
    for h in hashsums:
        assert h in hashers_old
        assert h in hashers_new

        patch_size += fpp.write('1-{}: '.format(h).encode('utf-8'))
        hashers_old[h][0] = fpp.tell()
        patch_size += fpp.write('{}\n'.format('X' * len(hashers_old[h][1].hexdigest())).encode('utf-8'))

        patch_size += fpp.write('2-{}: '.format(h).encode('utf-8'))
        hashers_new[h][0] = fpp.tell()
        patch_size += fpp.write('{}\n'.format('X' * len(hashers_new[h][1].hexdigest())).encode('utf-8'))

    # Заголовки закончились, дальше сам патч
    patch_size += fpp.write(b'\n')

    # Чтобы не дробить патч на слишком мелкие блоки (при маленьком значении
    # block_size_in), коллекционируем изменения в буфере, пока размер его
    # не достигнет block_size_out
    last_act = '='
    last_size = 0
    last_data1 = []
    last_data2 = []

    block_size_in = min(block_size_in, block_size_out or block_size_in)

    # Читаем оба файла, считая разницу
    for action, data_old, data_new in _bindiff(fp1, fp2, block_size_in=block_size_in):
        # Техническая всячина
        if verbose:
            tm2 = time.time()
            if tm2 - tm > 0.1:
                tm = tm2
                vprint(changed_cnt, all_cnt, bytes_processed, file_size)

        all_cnt += 1
        bytes_processed += max(len(data_old), len(data_new))

        # Если действие не то, которое в буфере, то сбрасываем буфер в файл
        if action != last_act:
            patch_size += _flush_buf(fpp, last_act, last_data1, last_data2, skip_del=skip_del)
            last_size = 0
            last_act = action

        # Откладываем изменения в буфер
        last_data1.append(data_old)
        last_data2.append(data_new)
        if action != '=':  # Считаем статистику
            changed_cnt += 1

        # Считаем размер данных в буфере
        last_size += max(len(data_old), len(data_new))
        # Если превысил максимум, то сбрасываем его в файл
        if block_size_out and last_size >= block_size_out:
            patch_size += _flush_buf(fpp, last_act, last_data1, last_data2, skip_del=skip_del)
            last_size = 0

        # Попутно считаем sha256sum обоих файлов
        for h in hashsums:
            hashers_old[h][1].update(data_old)
            hashers_new[h][1].update(data_new)

    # После цикла весь файл прочитан и разница посчитана, но это ещё не всё!
    if verbose:
        vprint(changed_cnt, all_cnt, bytes_processed, file_size)
    # Сбрасываем остатки буфера
    patch_size += _flush_buf(fpp, last_act, last_data1, last_data2, skip_del=skip_del)
    fpp.flush()

    # Мы считали хэш-суммы, возвращаемся в начало файла и пишем их
    if hashsums:
        for tell, hasher in sorted(list(hashers_old.values()) + list(hashers_new.values()), key=lambda x: x[0]):
            fpp.seek(tell)
            fpp.write(hasher.hexdigest().encode('utf-8'))  # patch_size не считаем, т.к. мы перезаписываем поверх

        fpp.seek(0, 2)

    if verbose:
        print('', file=sys.stderr)

    return {
        'patch_size': patch_size,
        'bytes_processed': bytes_processed,
        'block_size': block_size_in,
        'blocks_count': all_cnt,
        'changed_blocks_count': changed_cnt,
        'hashsums1': {k: h[1].hexdigest() for k, h in hashers_old.items()},
        'hashsums2': {k: h[1].hexdigest() for k, h in hashers_new.items()},
    }


def create_bindiff_from_empty(fp2, fpp, file_size, meta=None, hashsums=('sha256sum',), verbose=0):
    '''Конвертирует файл в патч так, будто первый файл является пустым.
    В отличие от обычной функции ``create_bindiff``, пишет в патч один большой
    блок со всем содержимым файла, чтоб занимало меньше места. Возвращает
    словарь со всякой разной статистикой.

    :param fp2: file-подобный объект
    :param fpp: файл, куда будет записываться патч (file-подобный объект;
      при указанных хэшах требуется поддержка seek и tell)
    :param int file_size: размер файла, из которого создаётся патч
    :param dict meta: словарь с заголовками, которые будут записаны в начале
      патча перед самими блоками с разницей
    :param tuple hashsums: перечисление хэшей, которые нужно посчитать и
      записать в заголовки в файл патча; требуют поддержки seek и tell от fpp
    :param int verbose: если не ноль, то печатается прогресс в stderr
    '''

    if verbose:
        print('\rOld file is empty, copying new file', end='', file=sys.stderr)
        sys.stderr.flush()

    patch_size = 0

    # Подсчёт хэшей аналогичен create_bindiff, но с поправкой на один файл
    hashers_new = create_hashers(hashsums)
    empty_hashes = {}

    # Пишем заголовок патча
    patch_size += fpp.write(b'abindiff 001\n')

    # После заголовка пишем всякую разную мету
    if meta:
        for k, v in meta.items():
            patch_size += fpp.write('{}: {}\n'.format(k.lower(), v).encode('utf-8'))

    for h in hashsums:
        assert h in hashers_new

        # Вместо отсутствующего первого файла заглушка с хэшем пустоты
        empty_hashes[h] = hashers_new[h][1].hexdigest()
        patch_size += fpp.write('1-{}: {}\n'.format(h, empty_hashes[h]).encode('utf-8'))

        patch_size += fpp.write('2-{}: '.format(h).encode('utf-8'))
        hashers_new[h][0] = fpp.tell()
        patch_size += fpp.write('{}\n'.format('X' * len(hashers_new[h][1].hexdigest())).encode('utf-8'))

    # Заголовки закончились, дальше сам патч
    patch_size += fpp.write(b'\n')

    # Относительно пустоты вся разница — добавление одного большого куска
    patch_size += fpp.write('+ {}\n\n'.format(file_size).encode('utf-8'))

    # Дальше просто копируем содержимое файла в патч
    cnt = 0
    while True:
        chunk = fp2.read(32768)
        if not chunk:
            break
        cnt += len(chunk)
        cnt2 = fpp.write(chunk)
        assert len(chunk) == cnt2
        patch_size += cnt

        for h in hashsums:
            hashers_new[h][1].update(chunk)

    # Проверяем, что с размером файла не обманули
    assert cnt == file_size

    patch_size += fpp.write(b'\n\n')
    fpp.flush()

    # Возвращаемся в начало и пишем хэш файла
    if hashsums:
        for tell, hasher in sorted(hashers_new.values(), key=lambda x: x[0]):
            fpp.seek(tell)
            fpp.write(hasher.hexdigest().encode('utf-8'))

        fpp.seek(0, 2)

    if verbose:
        print()

    return {
        'patch_size': patch_size,
        'bytes_processed': file_size,
        'block_size': file_size,
        'blocks_count': 1,
        'changed_blocks_count': 1,
        'hashsums1': empty_hashes,
        'hashsums2': {k: h[1].hexdigest() for k, h in hashers_new.items()},
    }


def create_bindiff_for_files(
    file1, file2, file_patch, gzip_level=-1, allow_empty=False,
    block_size_in=1024, block_size_out=1024 ** 2 * 32, skip_del=False,
    mtime=True, modes=True, hashsums=('sha256sum',), verbose=0
):
    '''Поблочно считает разницу между двумя файлами и записывает патч
    в третий файл. Также считает различную мета-информацию вроде прав доступа
    или дат изменения. Возвращает словарь со всякой разной статистикой.

    :param file1: путь к первому файлу
    :param file2: путь ко второму файлу
    :param file_patch: путь к файлу, куда будет записываться патч
    :param int gzip_level: уровень gzip-сжатия для файла с патчем
      (1-9, 0 — не сжимать, -1 — определить по расширению файла)
    :param bool allow_empty: при True разрешается отсутствие первого файла;
      тогда он неявно считается пустым файлом 1970 года выпуска
    :param int block_size_in: размер блоков, которые будут читаться
      и сравниваться (не может быть больше block_size_out)
    :param int block_size_out: максимальный размер блоков, которые будут
      записываться в патч (если 0, то неограниченно, но это может скушать
      оперативную память)
    :param bool skip_del: если True, то в патч не будет записываться
      содержимое удалённых кусков файла. Так патч станет весить примерно
      в два раза меньше, но его нельзя будет откатить
    :param bool mtime: если True, сохраняет даты изменения файлов в патч
    :param bool modes: если True, сохраняет POSIX права файлов в патч
    :param tuple hashsums: перечисление хэшей, которые нужно посчитать и
      записать в заголовки в файл патча; требуют поддержки seek и tell от fpp
    :param int verbose: если не ноль, то печатается прогресс в stderr
    '''

    # Выбираем уровень сжатия gzip
    if gzip_level not in range(0, 9 + 1):
        gzip_level = 4 if file_patch.lower().endswith('.gz') else 0

    # Готовим мета-информацию о файле
    # (первый файл возможно не существует, вместо него пока что заглушки)
    meta = {}
    if mtime:
        meta['1-mtime'] = '1970-01-01T00:00:00.000000Z'
        meta['2-mtime'] = datetime.utcfromtimestamp(os.stat(file2).st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    if modes:
        meta['1-mode'] = '---------'
        meta['2-mode'] = stat.filemode(os.stat(file2).st_mode)[1:]

    # Если нужен gzip, то тогда не работают seek и tell, и придётся посчитать
    # хэши заранее, так как они в начале файла
    # (существование первого файла ещё не проверено, считаем хэш для второго)
    if gzip_level > 0:
        hashsums_lazy = ()

        hashers = create_hashers(hashsums)

        # Ставим заглушку для возможно отсутствующего файла
        for h in hashsums:
            meta['1-' + h] = hashers[h][1].hexdigest()

        if verbose:
            print('\rPrecalc 2 hashsum', file=sys.stderr, end='')
            sys.stderr.flush()

        # Собственно считаем хэш
        with open(file2, 'rb') as hfp2:
            while True:
                chunk = hfp2.read(32768)
                if not chunk:
                    break
                for h in hashsums:
                    hashers[h][1].update(chunk)

        # Результат пихаем в мету
        for h in hashsums:
            meta['2-' + h] = hashers[h][1].hexdigest()
    else:
        # Без гзипа посчитаем хэши потом
        hashsums_lazy = hashsums
        # Но всё равно заранее проведём валидацию, что список хэшей правильный
        create_hashers(hashsums_lazy)

    # Если первый файл существует, то читаем его мета-информацию
    if os.path.exists(file1):
        if mtime:
            meta['1-mtime'] = datetime.utcfromtimestamp(os.stat(file1).st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        if modes:
            meta['1-mode'] = stat.filemode(os.stat(file1).st_mode)[1:]

    # Если нам разрешают ускорить работу с несуществующим или пустым первым
    # файлом — пользуемся этим!
    if allow_empty and (not os.path.exists(file1) or os.stat(file1).st_size == 0):
        file_size = os.stat(file2).st_size

        with open(file2, 'rb') as fp2:
            if gzip_level > 0:
                fpp = gzip.open(file_patch, 'wb', compresslevel=gzip_level)
            else:
                fpp = open(file_patch, 'wb')
            with fpp:
                return create_bindiff_from_empty(
                    fp2, fpp, file_size=file_size, meta=meta,
                    hashsums=hashsums_lazy, verbose=verbose
                )

    # Если оба файла не пусты, то идём дальше
    # Получаем больший размер для вывода прогресса в консоль
    file_size = max(
        os.stat(file1).st_size,
        os.stat(file2).st_size,
    )

    # Помните, у нас был гзип? Так вот, для первого файла хэш тоже надо будет
    # заранее посчитать
    if gzip_level > 0:
        hashers = create_hashers(hashsums)

        if verbose:
            print('\rPrecalc 1 hashsum', file=sys.stderr, end='')
            sys.stderr.flush()

        with open(file1, 'rb') as hfp1:
            while True:
                chunk = hfp1.read(32768)
                if not chunk:
                    break
                for h in hashsums:
                    hashers[h][1].update(chunk)

        for h in hashsums:
            meta['1-' + h] = hashers[h][1].hexdigest()

    # Открываем файлы на чтение и пишем патч
    with open(file1, 'rb') as fp1:
        with open(file2, 'rb') as fp2:
            if gzip_level > 0:
                fpp = gzip.open(file_patch, 'wb', compresslevel=gzip_level)
            else:
                fpp = open(file_patch, 'wb')
            with fpp:
                return create_bindiff(
                    fp1, fp2, fpp, block_size_in=block_size_in, block_size_out=block_size_out,
                    file_size=file_size, skip_del=skip_del, meta=meta,
                    hashsums=hashsums_lazy, verbose=verbose,
                )


# utils


def create_hashers(hashsums):
    hashers = {}
    if 'md5sum' in hashsums:
        hashers['md5sum'] = [None, hashlib.md5()]
    if 'sha1sum' in hashsums:
        hashers['sha1sum'] = [None, hashlib.sha1()]
    if 'sha256sum' in hashsums:
        hashers['sha256sum'] = [None, hashlib.sha256()]
    unknown = set(hashsums) - set(hashers)
    if unknown:
        raise ValueError('Unknown hashers: {}'.format(', '.join(unknown)))
    return hashers


def vprint(changed_cnt, all_cnt, bytes_processed, file_size=None):
    print('\r', end='', file=sys.stderr)
    if file_size:
        print('{:.2f}%'.format(bytes_processed * 100.0 / file_size), end=' ', file=sys.stderr)
    print('read {} blocks, changed {} blocks'.format(all_cnt, changed_cnt), end=' ', file=sys.stderr)
    sys.stderr.flush()


# console script


def main():
    parser = argparse.ArgumentParser(description='Generates block-by-block diff between two binary files')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='show progress')
    parser.add_argument('-M', '--nomtime', action='store_true', default=False, help='do not store modification date')
    parser.add_argument('-P', '--nomode', action='store_true', default=False, help='do not store POSIX file mode')
    parser.add_argument('-H', '--hash', default='sha256sum', help='calculate hashsums for old and new files (comma separated) (md5sum, sha1sum and/or sha256sum) (default: sha256sum)')
    parser.add_argument('-e', '--allow-empty', action='store_true', default=False, help='interpret non-existing input files as empty files')
    parser.add_argument('-d', '--skip-del', action='store_true', default=False, help='do not store deleted blocks in patch (smaller, but this patch cannot be revertible)')
    parser.add_argument('-b', '--block-size', type=int, default=1024, help='block size in bytes (1 will generate byte-to-byte diff; default 1024)')
    parser.add_argument('-z', '--gzip', type=int, default=-1, help='gzip compression level (1-9), 0 disables it, default 4 with .gz extension')
    parser.add_argument('file1', metavar='FILE1')
    parser.add_argument('file2', metavar='FILE2')
    parser.add_argument('patch', metavar='PATCHFILE')

    args = parser.parse_args()

    create_bindiff_for_files(
        args.file1,
        args.file2,
        args.patch,
        gzip_level=args.gzip,
        allow_empty=args.allow_empty,
        block_size_in=args.block_size,
        mtime=not args.nomtime,
        modes=not args.nomode,
        skip_del=args.skip_del,
        verbose=args.verbose,
        hashsums=[x.strip().lower() for x in args.hash.split(',') if x.strip()],
    )

    return 0


if __name__ == '__main__':
    sys.exit(main())
