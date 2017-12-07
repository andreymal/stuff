#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
from io import BytesIO

import pytest

from abindiff import patch



def test_read_headers_ok():
    fpp = BytesIO('abindiff 001\nfoo: 1\nbar: юни:код\n\nthis should be ignored'.encode('utf-8'))

    assert patch.read_headers(fpp) == {'foo': '1', 'bar': 'юни:код'}
    assert fpp.read() == b'this should be ignored'


def test_read_headers_ok_empty_patch():
    fpp = BytesIO(b'abindiff 001\na:5\n\n')

    assert patch.read_headers(fpp) == {'a': '5'}
    assert fpp.read() == b''


def test_read_headers_ok_empty_headers():
    fpp = BytesIO(b'abindiff 001\n\nq')

    assert patch.read_headers(fpp) == {}
    assert fpp.read() == b'q'


def test_read_headers_ok_empty_all():
    fpp = BytesIO(b'abindiff 001\n\n')

    assert patch.read_headers(fpp) == {}
    assert fpp.read() == b''


def test_read_headers_fail_version():
    fpp = BytesIO(b'abindiff 000\na: 5\n\n')

    with pytest.raises(ValueError):
        patch.read_headers(fpp)


def test_read_headers_fail_eof():
    fpp = BytesIO(b'abindiff 001\na: 5\nb:')

    with pytest.raises(ValueError):
        patch.read_headers(fpp)


def test_read_headers_fail_big():
    fpp = BytesIO(b'abindiff 001\na: ' + (b'0' * 65534) + b'5\n\nq')

    with pytest.raises(ValueError):
        patch.read_headers(fpp)


#


def test_read_patch_ok():
    fpp = BytesIO(b'''abindiff 001
a: 5
b: 6

= 3

+ 1 | a

- 2 foo=bar;baz=baq;  ; ;e=f | bc

- 3 skip=1

+ 5 ;;;;; | 12345

= 666 | '''.replace(b' | ', b'\n\n'))

    result = [
        ('h', {'a': '5', 'b': '6'}, None),
        ('=', {}, 3),
        ('+', {}, b'a'),
        ('-', {'foo': 'bar', 'baz': 'baq', 'e': 'f'}, b'bc'),
        ('-', {'skip': '1'}, 3),  # особый заголовок для экономии места
        ('+', {}, b'12345'),
        ('=', {}, 666),
    ]
    result.reverse()

    for x in patch.read_patch(fpp):
        assert x == result.pop()

    assert not result


def test_read_patch_ok_skip_headers():
    fpp = BytesIO(b'''abindiff 001
a: 5
b: 6

= 3 | '''.replace(b' | ', b'\n\n'))

    patch.read_headers(fpp)

    result = [
        ('h', {'fake': '1'}, None),
        ('=', {}, 3),
    ]
    result.reverse()

    for x in patch.read_patch(fpp, headers={'fake': '1'}):
        assert x == result.pop()

    assert not result


def test_read_patch_ok_max_block_size():
    fpp = BytesIO(b'''abindiff 001

= 777

- 15 skip=1

- 9 a=1 | 123456789

+ 9 | 987654321'''.replace(b' | ', b'\n\n'))

    result = [
        ('h', {}, None),
        ('=', {}, 777),
        ('-', {'skip': '1'}, 15),
        ('-', {'a': '1'}, b'1234'),
        ('-', {'a': '1'}, b'5678'),
        ('-', {'a': '1'}, b'9'),
        ('+', {}, b'9876'),
        ('+', {}, b'5432'),
        ('+', {}, b'1'),
    ]
    result.reverse()

    for x in patch.read_patch(fpp, max_block_size=4):
        assert x == result.pop()

    assert not result


def test_read_patch_ok_no_max_block_size():
    fpp = BytesIO(b'''abindiff 001

= 777

- 15 skip=1

- 9 a=1 | 123456789

+ 9 | 987654321'''.replace(b' | ', b'\n\n'))

    result = [
        ('h', {}, None),
        ('=', {}, 777),
        ('-', {'skip': '1'}, 15),
        ('-', {'a': '1'}, b'123456789'),
        ('+', {}, b'987654321'),
    ]
    result.reverse()

    for x in patch.read_patch(fpp, max_block_size=0):
        assert x == result.pop()

    assert not result


#


def test_apply_patch_ok_full(data_path):
    with open(os.path.join(data_path, 'old', 'unicode_file.txt'), 'rb') as rfp1:
        fp1 = BytesIO(rfp1.read())
    with open(os.path.join(data_path, 'patch_full', 'unicode_file.txt.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read())

    fp2 = BytesIO()

    patch.apply_patch(fp1, fp2, fpp)

    assert fp2.getvalue() == 'Петя\n'.encode('utf-8')


def test_apply_patch_ok_short(data_path):
    with open(os.path.join(data_path, 'old', 'unicode_file.txt'), 'rb') as rfp1:
        fp1 = BytesIO(rfp1.read())
    with open(os.path.join(data_path, 'patch_short', 'unicode_file.txt.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read())

    fp2 = BytesIO()

    patch.apply_patch(fp1, fp2, fpp)

    assert fp2.getvalue() == 'Петя\n'.encode('utf-8')


def test_apply_patch_fail_invalid_old_hash(data_path):
    with open(os.path.join(data_path, 'old', 'unicode_file.txt'), 'rb') as rfp1:
        fp1 = BytesIO(rfp1.read())
    with open(os.path.join(data_path, 'patch_full', 'unicode_file.txt.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read().replace(b'1-sha256sum: 3', b'1-sha256sum: f'))

    fp2 = BytesIO()

    with pytest.raises(ValueError) as excinfo:
        patch.apply_patch(fp1, fp2, fpp)

    assert str(excinfo.value) == 'sha256sum of old file is not equal'


def test_apply_patch_fail_invalid_new_hash(data_path):
    with open(os.path.join(data_path, 'old', 'unicode_file.txt'), 'rb') as rfp1:
        fp1 = BytesIO(rfp1.read())
    with open(os.path.join(data_path, 'patch_full', 'unicode_file.txt.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read().replace(b'2-sha256sum: 7', b'2-sha256sum: f'))

    fp2 = BytesIO()

    with pytest.raises(ValueError) as excinfo:
        patch.apply_patch(fp1, fp2, fpp)

    assert str(excinfo.value) == 'sha256sum of new file is not equal'


def test_apply_patch_ok_dont_check_invalid_hash(data_path):
    with open(os.path.join(data_path, 'old', 'unicode_file.txt'), 'rb') as rfp1:
        fp1 = BytesIO(rfp1.read())
    with open(os.path.join(data_path, 'patch_full', 'unicode_file.txt.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read().replace(b'1-sha256sum: 3', b'1-sha256sum: f').replace(b'2-sha256sum: 7', b'2-sha256sum: f'))

    fp2 = BytesIO()

    patch.apply_patch(fp1, fp2, fpp, check_hashsum=False)

    assert fp2.getvalue() == 'Петя\n'.encode('utf-8')


def test_apply_patch_ok_empty_hash(data_path):
    with open(os.path.join(data_path, 'old', 'unicode_file.txt'), 'rb') as rfp1:
        fp1 = BytesIO(rfp1.read())
    with open(os.path.join(data_path, 'patch_full', 'unicode_file.txt.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read().replace(b'1-sha256sum:', b'1-sha000sum:').replace(b'2-sha256sum: 7', b'2-sha000sum: f'))

    fp2 = BytesIO()

    patch.apply_patch(fp1, fp2, fpp)

    assert fp2.getvalue() == 'Петя\n'.encode('utf-8')


def test_apply_patch_fail_empty_hash_if_force_check(data_path):
    with open(os.path.join(data_path, 'old', 'unicode_file.txt'), 'rb') as rfp1:
        fp1 = BytesIO(rfp1.read())
    with open(os.path.join(data_path, 'patch_full', 'unicode_file.txt.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read().replace(b'1-sha256sum:', b'1-sha000sum:').replace(b'2-sha256sum:', b'2-sha000sum:'))

    fp2 = BytesIO()

    with pytest.raises(ValueError) as excinfo:
        patch.apply_patch(fp1, fp2, fpp, check_hashsum=True)

    assert str(excinfo.value) == 'This patch has no checksums'


def test_apply_patch_revert_ok_full(data_path):
    with open(os.path.join(data_path, 'new', 'unicode_file.txt'), 'rb') as rfp1:
        fp1 = BytesIO(rfp1.read())
    with open(os.path.join(data_path, 'patch_full', 'unicode_file.txt.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read())

    fp2 = BytesIO()

    patch.apply_patch(fp1, fp2, fpp, revert=True)

    assert fp2.getvalue() == 'Вася\n'.encode('utf-8')


def test_apply_patch_revert_fail_short(data_path):
    with open(os.path.join(data_path, 'new', 'unicode_file.txt'), 'rb') as rfp1:
        fp1 = BytesIO(rfp1.read())
    with open(os.path.join(data_path, 'patch_short', 'unicode_file.txt.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read())

    fp2 = BytesIO()

    with pytest.raises(ValueError):
        patch.apply_patch(fp1, fp2, fpp, revert=True)


#


@pytest.mark.parametrize('f,revert', [
    ('unicode_file.txt', False), ('unicode_file.txt', True),
    ('bigger_file.txt', False), ('bigger_file.txt', True),
    ('smaller_file.txt', False), ('smaller_file.txt', True),
    ('directory/not_changed_file.txt', False), ('directory/not_changed_file.txt', True),
])
def test_apply_patch_inplace_ok_full(f, revert, data_path, media_path):
    # inplace тестируем не на BytesIO, а на реальных файлах, так как там проблемы бывают
    path = os.path.join(media_path, os.path.split(f)[-1])
    shutil.copy2(os.path.join(data_path, 'new' if revert else 'old', f), path)

    with open(os.path.join(data_path, 'patch_full', f + '.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read())

    with open(path, 'r+b') as fp1:
        patch.apply_patch_inplace(fp1, fpp, revert=revert)

    with open(os.path.join(data_path, 'old' if revert else 'new', f)) as fp:
        data_expected = fp.read()
    with open(path) as fp:
        data_actual = fp.read()
    assert data_expected == data_actual


@pytest.mark.parametrize('f', [
    'unicode_file.txt',
    'bigger_file.txt',
    'smaller_file.txt',
])
def test_apply_patch_inplace_fail_short_revert(f, data_path, media_path):
    path = os.path.join(media_path, os.path.split(f)[-1])
    shutil.copy2(os.path.join(data_path, 'new', f), path)

    with open(os.path.join(data_path, 'patch_short', f + '.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read())

    with open(path, 'r+b') as fp1:
        with pytest.raises(ValueError) as excinfo:
            patch.apply_patch_inplace(fp1, fpp, revert=True)
    print(str(excinfo.value))


@pytest.mark.parametrize('f,revert', [
    ('unicode_file.txt', False), ('unicode_file.txt', True),
    ('bigger_file.txt', False), ('bigger_file.txt', True),
    ('smaller_file.txt', False), ('smaller_file.txt', True),
    ('directory/not_changed_file.txt', False), ('directory/not_changed_file.txt', True),
])
def test_apply_patch_inplace_ok_ignore_hashsum_full(f, revert, data_path, media_path):
    path = os.path.join(media_path, os.path.split(f)[-1])
    shutil.copy2(os.path.join(data_path, 'new' if revert else 'old', f), path)

    with open(os.path.join(data_path, 'patch_full', f + '.abindiff'), 'rb') as rfpp:
        if revert:
            fpp = BytesIO(rfpp.read().replace(b'2-sha256sum: ', b'2-sha256sum: e'))
        else:
            fpp = BytesIO(rfpp.read().replace(b'1-sha256sum: ', b'1-sha256sum: e'))

    # При inplace проверять хэш исходного файла тяжеловато, так что
    # на данный момент он просто игнорируется

    with open(path, 'r+b') as fp1:
        patch.apply_patch_inplace(fp1, fpp, revert=revert)


@pytest.mark.parametrize('f', [
    'unicode_file.txt',
    'bigger_file.txt',
    'smaller_file.txt',
])
def test_apply_patch_inplace_ok_ignore_hashsum_short(f, data_path, media_path):
    path = os.path.join(media_path, os.path.split(f)[-1])
    shutil.copy2(os.path.join(data_path, 'old', f), path)

    with open(os.path.join(data_path, 'patch_short', f + '.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read().replace(b'1-sha256sum: ', b'1-sha256sum: e'))

    with open(path, 'r+b') as fp1:
        patch.apply_patch_inplace(fp1, fpp, revert=False)


@pytest.mark.parametrize('f,revert', [
    ('unicode_file.txt', False), ('unicode_file.txt', True),
    ('bigger_file.txt', False), ('bigger_file.txt', True),
    ('smaller_file.txt', False), ('smaller_file.txt', True),
    ('directory/not_changed_file.txt', False), ('directory/not_changed_file.txt', True),
])
def test_apply_patch_inplace_fail_hashsum_full(f, revert, data_path, media_path):
    path = os.path.join(media_path, os.path.split(f)[-1])
    shutil.copy2(os.path.join(data_path, 'new' if revert else 'old', f), path)

    with open(os.path.join(data_path, 'patch_full', f + '.abindiff'), 'rb') as rfpp:
        if revert:
            fpp = BytesIO(rfpp.read().replace(b'1-sha256sum: ', b'1-sha256sum: e'))
        else:
            fpp = BytesIO(rfpp.read().replace(b'2-sha256sum: ', b'2-sha256sum: e'))

    with open(path, 'r+b') as fp1:
        with pytest.raises(ValueError) as excinfo:
            patch.apply_patch_inplace(fp1, fpp, revert=revert)
    assert str(excinfo.value) == 'sha256sum of saved file is not equal'


@pytest.mark.parametrize('f', [
    'unicode_file.txt',
    'bigger_file.txt',
    'smaller_file.txt',
])
def test_apply_patch_inplace_fail_hashsum_short(f, data_path, media_path):
    path = os.path.join(media_path, os.path.split(f)[-1])
    shutil.copy2(os.path.join(data_path, 'old', f), path)

    with open(os.path.join(data_path, 'patch_short', f + '.abindiff'), 'rb') as rfpp:
        fpp = BytesIO(rfpp.read().replace(b'2-sha256sum: ', b'2-sha256sum: e'))

    with open(path, 'r+b') as fp1:
        with pytest.raises(ValueError) as excinfo:
            patch.apply_patch_inplace(fp1, fpp, revert=False)
    assert str(excinfo.value) == 'sha256sum of saved file is not equal'


def test_apply_patch_issue32228(media_path):
    # https://bugs.python.org/issue32228

    path = os.path.join(media_path, 'wtf.bin')
    with open(path, 'wb') as fp:
        fp.write(b'\x00' * 8192)

    fpp = BytesIO(b'''abindiff 001

- 4097 skip=1

+ 4097

''' + (b'\x01' * 4097) + b'''

= 1

- 4094 skip=1

''')

    with open(path, 'r+b') as fp1:
        patch.apply_patch_inplace(fp1, fpp)  # проверка, что не падает

    with open(path, 'rb') as fp:
        data_actual = fp.read()

    assert data_actual == (b'\x01' * 4097) + b'\x00'


def test_apply_patch_ok_stange(media_path):
    # Далее проверяется кривые патчи, когда сперва идёт +, а только потом -.
    # abindiff такие патчи не создаёт, но проверить не помешает (при revert
    # патчи по сути получаются такие). Также эти тесты демонстрируют, что +
    # означает не добавление, а замену куска данных в случае inplace
    # (в отличие от классических текстовых диффов)

    # FIXME: вариант, когда минуса вообще нет, хорошо бы тоже поддерживать,
    # но на данный момент не поддерживается

    path = os.path.join(media_path, 'test.bin')

    fpp = BytesIO(b'''= 1
+ 1 | 9
- 1 | 2
= 2
'''.replace(b'\n', b'\n\n').replace(b' | ', b'\n\n'))

    with open(path, 'wb') as fp2:
        patch.apply_patch(BytesIO(b'1234'), fp2, fpp, headers={
            '1-sha256sum': '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4',
            '2-sha256sum': '914c948388ae30bdb0179a2f7bc91836d6af004171af735188fc1b69c286c864',
        })

    with open(path, 'rb') as fp:
        data_actual = fp.read()

    assert data_actual == b'1934'


def test_apply_patch_ok_inplace_stange(media_path):
    path = os.path.join(media_path, 'test.bin')
    with open(path, 'wb') as fp:
        fp.write(b'1234')

    fpp = BytesIO(b'''= 1
+ 1 | 9
- 1 | 2
= 2
'''.replace(b'\n', b'\n\n').replace(b' | ', b'\n\n'))

    with open(path, 'r+b') as fp1:
        patch.apply_patch_inplace(fp1, fpp, headers={
            '1-sha256sum': 'should be ignored',
            '2-sha256sum': '914c948388ae30bdb0179a2f7bc91836d6af004171af735188fc1b69c286c864',
        })

    with open(path, 'rb') as fp:
        data_actual = fp.read()

    assert data_actual == b'1934'


def test_apply_patch_ok_revert_stange(media_path):
    path = os.path.join(media_path, 'test.bin')

    fpp = BytesIO(b'''= 1
+ 1 | 9
- 1 | 2
= 2
'''.replace(b'\n', b'\n\n').replace(b' | ', b'\n\n'))

    with open(path, 'wb') as fp2:
        patch.apply_patch(BytesIO(b'1934'), fp2, fpp, revert=True, headers={
            '1-sha256sum': '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4',
            '2-sha256sum': '914c948388ae30bdb0179a2f7bc91836d6af004171af735188fc1b69c286c864',
        })

    with open(path, 'rb') as fp:
        data_actual = fp.read()

    assert data_actual == b'1234'


def test_apply_patch_ok_revert_inplace_stange(media_path):
    path = os.path.join(media_path, 'test.bin')
    with open(path, 'wb') as fp:
        fp.write(b'1934')

    fpp = BytesIO(b'''= 1
+ 1 | 9
- 1 | 2
= 2
'''.replace(b'\n', b'\n\n').replace(b' | ', b'\n\n'))

    with open(path, 'r+b') as fp1:
        patch.apply_patch_inplace(fp1, fpp, revert=True, headers={
            '1-sha256sum': '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4',
            '2-sha256sum': 'should be ignored',
        })

    with open(path, 'rb') as fp:
        data_actual = fp.read()

    assert data_actual == b'1234'


def test_apply_patch_empty():
    fp1 = BytesIO()
    fp2 = BytesIO()
    fpp = BytesIO(
        b'abindiff 001\n'
        b'1-sha256sum: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
        b'2-sha256sum: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
        b'\n'
    )

    patch.apply_patch(fp1, fp2, fpp, check_hashsum=True)

    assert fp2.getvalue() == b''


def test_apply_patch_inplace_empty():
    fp1 = BytesIO()
    fpp = BytesIO(
        b'abindiff 001\n'
        b'1-sha256sum: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
        b'2-sha256sum: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
        b'\n'
    )

    patch.apply_patch_inplace(fp1, fpp, check_hashsum=True)

    assert fp1.getvalue() == b''


def test_apply_patch_empty_fail_hashsum():
    fp1 = BytesIO()
    fp2 = BytesIO()
    fpp = BytesIO(
        b'abindiff 001\n'
        b'1-sha256sum: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
        b'2-sha256sum: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b85f\n'
        b'\n'
    )

    with pytest.raises(ValueError):
        patch.apply_patch(fp1, fp2, fpp, check_hashsum=True)


def test_apply_patch_inplace_empty_fail_hashsum():
    fp1 = BytesIO()
    fpp = BytesIO(
        b'abindiff 001\n'
        b'1-sha256sum: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n'
        b'2-sha256sum: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b85f\n'
        b'\n'
    )

    with pytest.raises(ValueError):
        patch.apply_patch_inplace(fp1, fpp, check_hashsum=True)


#

@pytest.mark.parametrize('f,mtime', [
    ('unicode_file.txt', 1512069655.527419),
    ('bigger_file.txt', 1512069636.650682),
    ('smaller_file.txt', 1512069644.304044),
    ('created_file.txt', 1512069627.247313),
    ('directory/not_changed_file.txt', 1512069596.240531),
])
def test_apply_patch_for_files_complex(f, mtime, data_path, media_path):
    file_input = os.path.join(data_path, 'old', f)
    file_expected = os.path.join(data_path, 'new', f)
    file_output = os.path.join(media_path, os.path.split(f)[-1])
    file_patch = os.path.join(data_path, 'patch_full', f + '.abindiff')

    patch.apply_patch_for_files(file_input, file_output, file_patch, allow_empty=f == 'created_file.txt')

    with open(file_output, 'rb') as fp:
        data_actual = fp.read()
    with open(file_expected, 'rb') as fp:
        data_expected = fp.read()

    assert data_expected == data_actual

    assert abs(os.stat(file_output).st_mtime - mtime) < 0.002


@pytest.mark.parametrize('f,mtime', [
    ('unicode_file.txt', 1512069655.527419),
    ('bigger_file.txt', 1512069636.650682),
    ('smaller_file.txt', 1512069644.304044),
    ('created_file.txt', 1512069627.247313),
    ('directory/not_changed_file.txt', 1512069596.240531),
])
def test_apply_patch_for_files_complex_gzip_auto(f, mtime, data_path, media_path):
    file_input = os.path.join(data_path, 'old', f)
    file_expected = os.path.join(data_path, 'new', f)
    file_output = os.path.join(media_path, os.path.split(f)[-1])
    file_patch = os.path.join(data_path, 'patch_gzip', f + '.abindiff.gz')

    patch.apply_patch_for_files(file_input, file_output, file_patch, allow_empty=f == 'created_file.txt')

    with open(file_output, 'rb') as fp:
        data_actual = fp.read()
    with open(file_expected, 'rb') as fp:
        data_expected = fp.read()

    assert data_expected == data_actual

    assert abs(os.stat(file_output).st_mtime - mtime) < 0.002



@pytest.mark.parametrize('f,mtime', [
    ('unicode_file.txt', 1512069655.527419),
    ('bigger_file.txt', 1512069636.650682),
    ('smaller_file.txt', 1512069644.304044),
    ('created_file.txt', 1512069627.247313),
    ('directory/not_changed_file.txt', 1512069596.240531),
])
def test_apply_patch_for_files_complex_noapply_meta(f, mtime, data_path, media_path):
    file_input = os.path.join(data_path, 'old', f)
    file_expected = os.path.join(data_path, 'new', f)
    file_output = os.path.join(media_path, os.path.split(f)[-1])
    file_patch = os.path.join(data_path, 'patch_full', f + '.abindiff')

    patch.apply_patch_for_files(file_input, file_output, file_patch, allow_empty=f == 'created_file.txt', apply_meta=False)

    with open(file_output, 'rb') as fp:
        data_actual = fp.read()
    with open(file_expected, 'rb') as fp:
        data_expected = fp.read()

    assert data_expected == data_actual

    assert abs(os.stat(file_output).st_mtime - mtime) > 60.0


@pytest.mark.parametrize('f,mtime', [
    ('unicode_file.txt', 1512069655.527419),
    ('bigger_file.txt', 1512069636.650682),
    ('smaller_file.txt', 1512069644.304044),
    ('created_file.txt', 1512069627.247313),
    ('directory/not_changed_file.txt', 1512069596.240531),
])
def test_apply_patch_for_files_complex_empty_meta(f, mtime, data_path, media_path):
    file_input = os.path.join(data_path, 'old', f)
    file_expected = os.path.join(data_path, 'new', f)
    file_output = os.path.join(media_path, os.path.split(f)[-1])
    file_patch = os.path.join(data_path, 'patch_nometa', f + '.abindiff')

    patch.apply_patch_for_files(file_input, file_output, file_patch, allow_empty=f == 'created_file.txt', apply_meta=True)

    with open(file_output, 'rb') as fp:
        data_actual = fp.read()
    with open(file_expected, 'rb') as fp:
        data_expected = fp.read()

    assert data_expected == data_actual

    assert abs(os.stat(file_output).st_mtime - mtime) > 60.0


@pytest.mark.parametrize('f,mtime', [
    ('unicode_file.txt', 1512069655.527419),
    ('bigger_file.txt', 1512069636.650682),
    ('smaller_file.txt', 1512069644.304044),
    ('created_file.txt', 1512069627.247313),
    ('directory/not_changed_file.txt', 1512069596.240531),
])
def test_apply_patch_for_files_inplace(f, mtime, data_path, media_path):
    file_input = os.path.join(data_path, 'old', f)
    file_expected = os.path.join(data_path, 'new', f)
    file_output = os.path.join(media_path, os.path.split(f)[-1])
    file_patch = os.path.join(data_path, 'patch_full', f + '.abindiff')

    if f == 'created_file.txt':
        with open(file_output, 'wb'):
            pass  # touch
    else:
        shutil.copy(file_input, file_output)

    patch.apply_patch_for_files(file_output, file_output, file_patch, allow_empty=f == 'created_file.txt')

    with open(file_output, 'rb') as fp:
        data_actual = fp.read()
    with open(file_expected, 'rb') as fp:
        data_expected = fp.read()

    assert data_expected == data_actual

    assert abs(os.stat(file_output).st_mtime - mtime) < 0.002
