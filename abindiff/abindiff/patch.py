#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import io
import sys
import gzip
import hashlib
import argparse
from datetime import datetime


def read_headers(fpp):
    # Читает заголовки из начала патча до получения \n\n включительно

    header = fpp.read(13)
    if header != b'abindiff 001\n':
        raise ValueError('Unknown patch format')

    data = b'\n'
    while not data.endswith(b'\n\n'):
        b = fpp.read(1)
        if not b:
            break
        data += b
        if len(data) > 65535:
            raise ValueError('too many headers')

    if not data.endswith(b'\n\n'):
        raise ValueError('Unexpected end of patch while reading headers')

    headers_list = data.decode('utf-8').strip().split('\n')
    headers = {}
    for h in headers_list:
        if not h:
            continue
        k, v = h.split(':', 1)
        headers[k.lower().strip()] = v.strip()
    return headers


def read_patch(fpp, headers=None, max_block_size=1024 ** 2 * 16):
    '''Парсит патч, читая file-подобный объект. Генератор, для каждого
    успешного чтения возвращает кортеж из трёх элементов: тип, заголовки
    и данные. Формат данных зависит от типа:

    - тип ``h`` — прочитана мета в начале файла, данных нет;
    - тип ``=`` — длина совпадающих данных;
    - тип ``-`` — с заголовком ``skip=1`` длина удалённых данных, иначе —
      удалённый кусок;
    - тип ``+`` — добавленный кусок.

    Если не указать ``headers``, то будет читать заголовки как из начала
    файла; если указать, то не будет, а сразу перейдёт к чтению самого патча.

    :param fpp: читаемый файл
    :param dict headers: словарь с заголовками (если уже были прочитаны)
    :param int max_block_size: максимальный размер читаемого блока. Если
      в файле есть блоки большего размера, они при чтении будут разбиты
      на несколько меньших блоков
    '''

    if headers is None:
        headers = read_headers(fpp)
    yield 'h', headers, None

    while True:
        # read action header
        act = b''
        while not act.endswith(b'\n\n'):
            tmp = fpp.read(1)
            if not tmp:
                if act:
                    raise ValueError('Unexpected end of patch while reading action')
                return
            act += tmp
            if len(act) > 255:
                raise ValueError('Too big action header')

        # parse action header
        if b' ' not in act:
            raise ValueError('Bad action header format')
        act, size = act.rstrip().split(b' ', 1)
        if b' ' in size:
            size, raw_headers = size.split(b' ', 1)
        else:
            size, raw_headers = size, b''

        if act not in (b'=', b'-', b'+'):
            raise ValueError('Bad action type')
        if not size.isdigit():
            raise ValueError('Bad action size')

        headers = {}
        for x in raw_headers.decode('utf-8').split(';'):
            x = x.strip()
            if not x:
                continue
            if '=' not in x:
                raise ValueError('Bad block header format')
            x = x.split('=', 1)
            headers[x[0]] = x[1]

        size = int(size)

        if act == b'=':
            yield '=', headers, size
            continue

        if act == b'-' and headers.get('skip') == '1':
            yield '-', headers, size
            continue

        # read data
        if max_block_size:
            cnt = 0
            while cnt < size:
                rsize = min(max_block_size, size - cnt)
                data = fpp.read(rsize)
                if len(data) != rsize:
                    raise ValueError('Unexpected end of patch while reading data')
                cnt += rsize
                yield act.decode(), headers, data

        else:
            data = fpp.read(size)
            if len(data) != size:
                raise ValueError('Unexpected end of patch while reading data')
            yield act.decode(), headers, data

        # read data ending
        footer = fpp.read(2)
        if footer not in (b'', b'\n\n'):
            raise ValueError('Bad data ending')

        if not footer:
            return


def _start_hashcalc(headers, check_hashsum):
    hash_type = None
    hash_old = None
    hash_new = None

    if check_hashsum or check_hashsum is None:
        if '1-sha256sum' in headers and '2-sha256sum' in headers:
            hash_type = 'sha256sum'
            hash_old = hashlib.sha256()
            hash_new = hashlib.sha256()
        elif '1-sha1sum' in headers and '2-sha1sum' in headers:
            hash_type = 'sha1sum'
            hash_old = hashlib.sha1()
            hash_new = hashlib.sha1()
        elif '1-md5sum' in headers and '2-md5sum' in headers:
            hash_type = 'md5sum'
            hash_old = hashlib.md5()
            hash_new = hashlib.md5()
        elif check_hashsum:
            raise ValueError('This patch has no checksums')

    return hash_type, hash_old, hash_new


def _revert_act(real_action, act_headers, revert):
    if real_action == '=':
        return '='

    if revert:
        if real_action == '+':
            if act_headers.get('skip') == '1':
                raise ValueError('wat')
            action = '-'
        elif real_action == '-':
            if act_headers.get('skip') == '1':
                raise ValueError('This patch is not revertible')
            action = '+'
        else:
            assert False
    else:
        action = real_action

    return action


def apply_patch(fp1, fp2, fpp, headers=None, revert=False, check_hashsum=None):
    '''Применяет патч к первому файлу, записывая результат во второй файл.

    Если не указать ``headers``, то будет читать заголовки как из начала
    файла; если указать, то не будет, а сразу перейдёт к чтению самого патча.

    :param fp1: первый файл (file-подобный объект), который будет читаться
    :param fp2: второй файл (file-подобный объект), в который будет
      записываться результат
    :param fpp: применяемый патч (file-подобный объект)
    :param dict headers: словарь с заголовками (если уже были прочитаны)
    :param bool revert: если True, применяет патч наоборот (откатывает его);
      может вытать ошибку, если в патче отсутствуют удалённые куски и откат
      невозможен
    :param check_hashsum: если None, проверяет хэш-суммы файлов при наличии;
      если False, не проверяет; если True, проверяет всегда, а при отсутствии
      хэшей в патче кидает ошибку
    '''

    # Попутно будем считать какой-нибудь хэш для проверки целостности
    # (revert здесь не учитывается)
    hash_type = None
    hash_old = None
    hash_new = None

    file_size = 0  # Считаем конечный размер файла

    for real_action, act_headers, data in read_patch(fpp, headers=headers):
        if real_action == 'h':
            headers = act_headers
            # Когда мы получили заголовки, можно посмотреть наличие хэшей и запустить их подсчёт
            hash_type, hash_old, hash_new = _start_hashcalc(headers, check_hashsum)
            continue

        action = _revert_act(real_action, act_headers, revert)

        if action == '=':
            # Одинаковые куски просто пишем из старого файла и пишем в новый
            size = data
            old_data = fp1.read(size)
            if len(old_data) != size:
                raise ValueError('Unexpected end of input file')
            fp2.write(old_data)
            file_size += size
            # Попутно хэш считаем
            if hash_old:
                hash_old.update(old_data)
            if hash_new:
                hash_new.update(old_data)

        elif action == '-':
            # При удалении куска читаем его из старого файла для трёх вещей:
            # 1) seek
            # 2) проверка целостности путём сравнения прочитанного с куском из патча (при наличии)
            # 3) проверка целостности путём подсчёта хэша
            data_skip = act_headers.get('skip') == '1'
            size = len(data) if not data_skip else data
            old_data = fp1.read(size)
            if not data_skip and old_data != data:
                raise ValueError('Invalid input file')
            if real_action == '-' and hash_old:
                hash_old.update(old_data)
            if real_action == '+' and hash_new:
                hash_new.update(old_data)

        elif action == '+':
            fp2.write(data)
            file_size += len(data)
            if real_action == '+' and hash_new:
                hash_new.update(data)
            if real_action == '-' and hash_old:
                hash_old.update(data)

    if hash_old:
        if hash_old.hexdigest() != headers['1-' + hash_type].lower():
            raise ValueError(hash_type + ' of old file is not equal')

    if hash_new:
        if hash_new.hexdigest() != headers['2-' + hash_type].lower():
            raise ValueError(hash_type + ' of new file is not equal')

    return {
        'file_size': file_size,
        'hash_old': hash_old.hexdigest() if hash_old else None,
        'hash_new': hash_new.hexdigest() if hash_old else None,
    }

def apply_patch_inplace(fp1, fpp, headers=None, revert=False, check_hashsum=None):
    '''Применяет патч к файлу, записывая результат прямо в него же.

    Если не указать ``headers``, то будет читать заголовки как из начала
    файла; если указать, то не будет, а сразу перейдёт к чтению самого патча.

    :param fp1: обрабатываемый файл (file-подобный объект)
    :param fpp: применяемый патч (file-подобный объект)
    :param dict headers: словарь с заголовками (если уже были прочитаны)
    :param bool revert: если True, применяет патч наоборот (откатывает его);
      может вытать ошибку, если в патче отсутствуют удалённые куски и откат
      невозможен
    :param check_hashsum: если None, проверяет хэш-суммы файлов при наличии;
      если False, не проверяет; если True, проверяет всегда, а при отсутствии
      хэшей в патче кидает ошибку
    '''

    # Попутно будем считать какой-нибудь хэш для проверки целостности
    # (в связи с техническими трудностями с revert считаем только пропатченый файл)
    hash_type = None
    hash_out = None

    file_size = 0  # Считаем конечный размер файла

    assert fp1.tell() == 0

    seek_back = 0  # Для нескольких '-' блоков подряд
    for real_action, act_headers, data in read_patch(fpp, headers=headers):
        if real_action == 'h':
            headers = act_headers
            hash_type, _, hash_out = _start_hashcalc(headers, check_hashsum)
            continue

        action = _revert_act(real_action, act_headers, revert)

        if action != '-' and seek_back:
            # Когда мы проверяли '-' блоки, мы не откатились назад, а надо;
            # '=' или '+' перезапишет блоки в файле, которые мы проверяли
            fp1.seek(-seek_back, 1)
            seek_back = 0

        if action == '=':
            size = data
            file_size += size
            old_data = fp1.read(size)
            if hash_out:
                hash_out.update(old_data)
            if len(old_data) != size:
                raise ValueError('Unexpected end of input file')

        elif action == '-':
            pass  # В старой версии кода здесь добавлялся seek_back и проверялись хэши, но тот код был глючен

        elif action == '+':
            l = fp1.write(data)
            assert l == len(data)
            file_size += l
            if hash_out:
                hash_out.update(data)

    if seek_back:
        fp1.seek(-seek_back, 1)
        seek_back = 0

    # Если пропатченый файл короче исходного, отрезаем лишнее
    fp1.truncate()  # Обрезка под текущую позицию
    # FIXME: этот ассерт временно не работает https://bugs.python.org/issue32228
    # assert fp1.tell() == file_size

    # Альтернатива неработающему ассерту, позже выпилить
    if file_size > 0:
        fp1.seek(file_size - 1)
        x = fp1.read(1024)
        assert len(x) == 1
        fp1.seek(file_size)

    if hash_out:
        if hash_out.hexdigest() != headers[('1-' if revert else '2-') + hash_type].lower():
            raise ValueError(hash_type + ' of saved file is not equal')

    return {
        'file_size': file_size,
        'hash_out': hash_out.hexdigest() if hash_out else None,
    }


def apply_patch_for_files(
    file_input, file_output, file_patch, use_gzip=None,
    allow_empty=False, revert=False, check_hashsum=None, apply_meta=True,
):
    '''Применяет патч к первому файлу, записывая результат во второй файл.
    В качестве файлов указываются пути; оба файла могут быть одним и тем же
    файлом, тогда патч применяется путём его перезаписи (осторожно, можно
    случайно угробить файл).

    :param file_input: путь к первому файлу, который будет читаться
    :param file_output: путь ко второму файлу, в который будет записываться
      результат
    :param file_patch: путь к применяемому патчу
    :param bool use_gzip: True — читать патч как gzip-файл, False — читать
      как обычный файл, None — определить по расширению
    :param bool allow_empty: при True разрешается отсутствие первого файла;
      тогда он неявно считается пустым файлом 1970 года выпуска
    :param bool revert: если True, применяет патч наоборот (откатывает его);
      может вытать ошибку, если в патче отсутствуют удалённые куски и откат
      невозможен
    :param check_hashsum: если None, проверяет хэш-суммы файлов при наличии;
      если False, не проверяет; если True, проверяет всегда, а при отсутствии
      хэшей в патче кидает ошибку
    :param bool apply_meta: если True, применяет к пропатченному файлу
      мета-информацию (POSIX-права, дата изменения) при её наличии в патче
    '''

    if use_gzip is None:
        use_gzip = file_patch.lower().endswith('.gz')

    file_input = os.path.abspath(file_input)
    file_output = os.path.abspath(file_output or file_input)

    # open patch
    if use_gzip:
        fpp = gzip.open(file_patch, 'rb')
    else:
        fpp = open(file_patch, 'rb')

    with fpp:
        # Читаем заголовки сильно заранее, чтобы безопасно упасть ошибкой, если патч кривой
        headers = read_headers(fpp)

        if file_input == file_output:
            # Патчим файл на месте
            with open(file_input, 'r+b') as fp1:
                result = apply_patch_inplace(fp1, fpp, headers=headers, revert=revert, check_hashsum=check_hashsum)

        else:
            # Патчим файл, записывая результат в новый файл
            if allow_empty and not os.path.exists(file_input):
                fp1 = io.BytesIO()
            else:
                fp1 = open(file_input, 'rb')

            with fp1:
                try:
                    # open output file and process
                    with open(file_output, 'wb') as fp2:
                        result = apply_patch(fp1, fp2, fpp, headers=headers, revert=revert, check_hashsum=check_hashsum)
                except:  # pragma: no cover
                    if os.path.isfile(file_output):
                        os.remove(file_output)
                    raise

    if apply_meta:
        apply_meta_for_file(file_output, headers, prefix='1-' if revert else '2-')

    return result


def apply_meta_for_file(path, headers, prefix='2-'):
    if prefix + 'mtime' in headers:
        mtime = datetime.strptime(headers[prefix + 'mtime'], '%Y-%m-%dt%H:%M:%S.%fZ')
        mtime = (mtime - datetime(1970, 1, 1, 0, 0, 0)).total_seconds()
        os.utime(path, (mtime, mtime))

    if prefix + 'mode' in headers:
        os.chmod(path, parse_mod_string(headers[prefix + 'mode']))


def parse_mod_string(s):
    result = 0
    assert len(s) == 9
    for k, v in zip(s, (
        0o400, 0o200, 0o100,
        0o040, 0o020, 0o010,
        0o004, 0o002, 0o001,
    )):
        if k != '-':
            result += v

    return result


def main():
    parser = argparse.ArgumentParser(description='Applies or reverts patch generated by abindiff')
    parser.add_argument('-R', '--revert', '--reverse', action='store_true', default=False, help='revert patch')
    parser.add_argument('-H', '--nohash', action='store_true', default=False, help='do not check hashsums')
    parser.add_argument('-M', '--nometa', action='store_true', default=False, help='do not apply meta information (mtime and POSIX file mode)')
    parser.add_argument('-e', '--allow-empty', action='store_true', default=False, help='interpret non-existing input files as empty files')
    parser.add_argument('-i', '--in-place', action='store_true', default=False, help='Apply patch in-place')
    parser.add_argument('-z', '--gzip', action='store_true', default=False, help='read patch as gzip file (default detected by extension)')
    parser.add_argument('-Z', '--no-gzip', action='store_true', default=False, help='do not read patch as gzip file (default detected by extension)')
    parser.add_argument('patch', metavar='PATCHFILE')
    parser.add_argument('file1', metavar='INPUT')
    parser.add_argument('file2', metavar='OUTPUT', nargs='?', default=None)

    args = parser.parse_args()

    if not args.file2:
        if not args.in_place:
            print('Please set output file or use --in-place option', file=sys.stderr)
            return 1

    in_place = args.in_place or os.path.abspath(args.file1) == os.path.abspath(args.file2)

    if args.gzip and args.no_gzip:
        print('Use only --gzip or --no-gzip', file=sys.stderr)
        return 1
    if args.gzip:
        use_gzip = True
    elif args.no_gzip:
        use_gzip = False
    else:
        use_gzip = None

    if not in_place and os.path.exists(args.file2):
        print('Output file already exists', file=sys.stderr)
        return 1

    apply_patch_for_files(
        file_input=args.file1,
        file_output=args.file2,
        file_patch=args.patch,
        use_gzip=use_gzip,
        allow_empty=args.allow_empty,
        revert=args.revert,
        check_hashsum=False if args.nohash else None,
        apply_meta=not args.nometa,
    )

    return 0


if __name__ == '__main__':
    sys.exit(main())
