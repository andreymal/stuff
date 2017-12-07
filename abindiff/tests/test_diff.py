#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import gzip
import stat
from io import BytesIO
from datetime import datetime

import pytest

from abindiff import diff


class NoSeekBytesIO(BytesIO):
    def seek(self, *args, **kwargs):
        assert False, 'seek called!'

    def tell(self, *args, **kwargs):
        assert False, 'tell called!'


def test_create_bindiff_empty(read_headers):
    fp1 = BytesIO(b'')
    fp2 = BytesIO(b'')
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp)

    assert not result['changed_blocks_count']
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        '2-sha256sum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    }

    assert fpp.read() == b''


def test_create_bindiff_nochanges():
    fp1 = BytesIO('Без изменений\n'.encode('utf-8'))
    fp2 = BytesIO('Без изменений\n'.encode('utf-8'))
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp)

    assert len(fpp.getvalue()) == result['patch_size']

    assert result['hashsums1']['sha256sum'] == 'ba1b721126a113051c7eff677dca6222001b51f4e272d956b25267a3bea8ca7d'
    assert result['hashsums2']['sha256sum'] == 'ba1b721126a113051c7eff677dca6222001b51f4e272d956b25267a3bea8ca7d'
    assert not result['changed_blocks_count']

    assert fpp.getvalue().endswith(b'\n\n= 26\n\n')


def test_create_bindiff_bigger(read_headers):
    fp1 = BytesIO(b'foobar')
    fp2 = BytesIO(b'foobarbaz')
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp, block_size_in=1)
    assert result['changed_blocks_count'] == 3
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': 'c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2',
        '2-sha256sum': '97df3588b5a3f24babc3851b372f0ba71a9dcdded43b14b9d06961bfc1707d9d',
    }

    assert fpp.read() == b'= 6\n\n+ 3\n\nbaz\n\n'


def test_create_bindiff_smaller(read_headers):
    fp1 = BytesIO(b'foobarbaz')
    fp2 = BytesIO(b'foobar')
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp, block_size_in=1)
    assert result['changed_blocks_count'] == 3
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': '97df3588b5a3f24babc3851b372f0ba71a9dcdded43b14b9d06961bfc1707d9d',
        '2-sha256sum': 'c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2',
    }

    assert fpp.read() == b'= 6\n\n- 3\n\nbaz\n\n'



def test_create_bindiff_middle(read_headers):
    fp1 = BytesIO(b'foobar')
    fp2 = BytesIO(b'foObar')
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp, block_size_in=1)
    assert result['changed_blocks_count'] == 1
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': 'c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2',
        '2-sha256sum': 'fcca220448e336a24021d0ae4a61a99ded738921d7eb13c96b9c40bf47b50a8e',
    }

    assert fpp.read() == b'= 2\n\n- 1\n\no\n\n+ 1\n\nO\n\n= 3\n\n'


def test_create_bindiff_middle_skipdel(read_headers):
    fp1 = BytesIO(b'foobar')
    fp2 = BytesIO(b'foObar')
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp, block_size_in=1, skip_del=True)
    assert result['changed_blocks_count'] == 1
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': 'c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2',
        '2-sha256sum': 'fcca220448e336a24021d0ae4a61a99ded738921d7eb13c96b9c40bf47b50a8e',
    }

    assert fpp.read() == b'= 2\n\n- 1 skip=1\n\n+ 1\n\nO\n\n= 3\n\n'


def test_create_bindiff_middle_bigblock(read_headers):
    fp1 = BytesIO(b'foobar')
    fp2 = BytesIO(b'foObar')
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp, block_size_in=1024)
    assert result['changed_blocks_count'] == 1
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': 'c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2',
        '2-sha256sum': 'fcca220448e336a24021d0ae4a61a99ded738921d7eb13c96b9c40bf47b50a8e',
    }

    assert fpp.read() == b'- 6\n\nfoobar\n\n+ 6\n\nfoObar\n\n'



def test_create_bindiff_middle_smallblockout(read_headers):
    fp1 = BytesIO(b'big YAY change')
    fp2 = BytesIO(b'big big change')
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp, block_size_in=1, block_size_out=2)
    assert result['changed_blocks_count'] == 3
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': 'd0816c2b7ec348487a76ade68ffc6ec0857f105ff70d679b3e31fc6ec31d31d8',
        '2-sha256sum': 'f8a3f03cf84bb26a22e3fa234c700238b195ec60438d1fc471167e49d7f16c9a',
    }

    assert fpp.read() == b'= 2\n\n= 2\n\n- 2\n\nYA\n\n+ 2\n\nbi\n\n- 1\n\nY\n\n+ 1\n\ng\n\n= 2\n\n= 2\n\n= 2\n\n= 1\n\n'


def test_create_bindiff_complex(read_headers):
    fp1 = BytesIO('Мама мыла раму!'.encode('utf-8'))
    fp2 = BytesIO('Папа кушал а я не придумал что он кушал, но не раму!'.encode('utf-8'))
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp, block_size_in=1)
    assert result['changed_blocks_count'] == 78
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': '52ba604c1f288ae450030d619d79a2d20c61df3b52ec634e03363619bd8d5465',
        '2-sha256sum': '68b89b4c8ab0587e264e7810fc30d5c87e13d873efd746886dcc912fd4dedf26',
    }

    # Да, это UTF-8! Диффалка порвала символы пополам
    data = (
        b'= 1\n\n- 1\n\n\x9c\n\n+ 1\n\n\x9f\n\n= 3\n\n- 1\n\n\xbc\n\n'
        b'+ 1\n\n\xbf\n\n= 4\n\n- 1\n\n\xbc\n\n+ 1\n\n\xba\n\n= 1\n\n'
        b'- 3\n\n\x8b\xd0\xbb\n\n+ 3\n\n\x83\xd1\x88\n\n= 2\n\n'
        b'- 3\n\n \xd1\x80\n\n+ 3\n\n\xd0\xbb \n\n= 2\n\n'
        b'- 5\n\n\xd0\xbc\xd1\x83!\n\n+ 69\n\n \xd1\x8f \xd0\xbd\xd0\xb5'
        b' \xd0\xbf\xd1\x80\xd0\xb8\xd0\xb4\xd1\x83\xd0\xbc\xd0\xb0\xd0\xbb'
        b' \xd1\x87\xd1\x82\xd0\xbe \xd0\xbe\xd0\xbd \xd0\xba\xd1\x83\xd1\x88'
        b'\xd0\xb0\xd0\xbb, \xd0\xbd\xd0\xbe \xd0\xbd\xd0\xb5 '
        b'\xd1\x80\xd0\xb0\xd0\xbc\xd1\x83!\n\n'
    )

    assert fpp.read() == data


def test_create_bindiff_complex_2block(read_headers):
    fp1 = BytesIO('Мама  мыла  раму!'.encode('utf-8'))
    fp2 = BytesIO('Папа  кушал  а  я  не  придумал  что  он  кушал,  но  не  раму!'.encode('utf-8'))
    fpp = BytesIO()

    result = diff.create_bindiff(fp1, fp2, fpp, block_size_in=2)
    assert result['changed_blocks_count'] == 46
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': '5669de59e1c798bf5a580bae005f1dc9eedc5fcea8986cd74f01ba085cbe5eec',
        '2-sha256sum': 'f019f0ad98a3d06b11165fb5d23ade69d6b94ec616ef471487bc6ce9c132d39e',
    }

    # В отличие от предыдущего теста, текст выровнен так, чтобы оставался корректный UTF-8
    data = '''- 2 | М
+ 2 | П
= 2
- 2 | м
+ 2 | п
= 4
- 6 | мыл
+ 6 | куш
= 2
- 4 |   р
+ 4 | л  
= 2
- 5 | му!
+ 78 |   я  не  придумал  что  он  кушал,  но  не  раму!
'''
    data = data.replace('\n', '\n\n')
    data = data.replace(' | ', '\n\n')
    data = data.encode('utf-8')

    assert fpp.read() == data


def test_create_bindiff_custom_meta(read_headers):
    fp1 = BytesIO(b'')
    fp2 = BytesIO(b'')
    fpp = BytesIO()

    diff.create_bindiff(fp1, fp2, fpp, meta={
        'бАр': ':=;©®™',
        'FoO': 'Вася',
    })

    assert read_headers(fpp) == {
        '1-sha256sum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        '2-sha256sum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'foo': 'Вася',  # Ключи заголовков всегда в нижем регистре
        'бар': ':=;©®™',
    }


def test_create_bindiff_all_hashes(read_headers):
    fp1 = BytesIO(b'a\n')
    fp2 = BytesIO(b'b\n')
    fpp = BytesIO()

    diff.create_bindiff(fp1, fp2, fpp, hashsums=('md5sum', 'sha1sum', 'sha256sum'))

    assert read_headers(fpp) == {
        '1-md5sum': '60b725f10c9c85c70d97880dfe8191b3',
        '2-md5sum': '3b5d5c3712955042212316173ccf37be',
        '1-sha1sum': '3f786850e387550fdab836ed7e6dc881de23001b',
        '2-sha1sum': '89e6c98d92887913cadf06b2adb97f26cde4849b',
        '1-sha256sum': '87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7',
        '2-sha256sum': '0263829989b6fd954f72baaf2fc64bc2e2f01d692d4de72986ea808f6e99813f',
    }


def test_create_bindiff_no_hashes(read_headers):
    fp1 = BytesIO(b'a\n')
    fp2 = BytesIO(b'b\n')
    fpp = NoSeekBytesIO()  # Без хэшей seek/tell использоваться не должны

    diff.create_bindiff(fp1, fp2, fpp, hashsums=())

    assert read_headers(BytesIO(fpp.getvalue())) == {}


def test_create_bindiff_unknown_hashes(read_headers):
    fp1 = BytesIO(b'a\n')
    fp2 = BytesIO(b'b\n')
    fpp = NoSeekBytesIO()  # Без хэшей seek/tell использоваться не должны

    with pytest.raises(ValueError):
        diff.create_bindiff(fp1, fp2, fpp, hashsums=('wtfsum',))

    assert not fpp.getvalue()

#


def test_create_bindiff_from_empty(read_headers):
    fp = BytesIO(b'very loooooong file')
    fpp = BytesIO()

    result = diff.create_bindiff_from_empty(fp, fpp, len(fp.getvalue()))

    assert result['hashsums1']['sha256sum'] == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    assert result['hashsums2']['sha256sum'] == '1e1d9dbc9cddf9d09224978735bfd6a556ff902567c4f9b10304d82058620f3c'
    assert result['changed_blocks_count'] == 1
    assert len(fpp.getvalue()) == result['patch_size']

    assert read_headers(fpp) == {
        '1-sha256sum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        '2-sha256sum': '1e1d9dbc9cddf9d09224978735bfd6a556ff902567c4f9b10304d82058620f3c',
    }

    assert fpp.read() == b'+ 19\n\nvery loooooong file\n\n'


def test_create_bindiff_from_empty_custom_meta(read_headers):
    fp = BytesIO(b'very loooooong file')
    fpp = BytesIO()

    diff.create_bindiff_from_empty(fp, fpp, len(fp.getvalue()), meta={
        'бАр': ':=;©®™',
        'FoO': 'Вася',
    })

    assert read_headers(fpp) == {
        '1-sha256sum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        '2-sha256sum': '1e1d9dbc9cddf9d09224978735bfd6a556ff902567c4f9b10304d82058620f3c',
        'foo': 'Вася',  # Ключи заголовков всегда в нижем регистре
        'бар': ':=;©®™',
    }



def test_create_bindiff_from_empty_no_hashes(read_headers):
    fp = BytesIO(b'very loooooong file')
    fpp = NoSeekBytesIO()

    diff.create_bindiff_from_empty(fp, fpp, len(fp.getvalue()), hashsums=())

    assert read_headers(BytesIO(fpp.getvalue())) == {}


#


def test_create_bindiff_for_files_complex(data_path, media_path, read_headers):
    file1 = os.path.join(data_path, 'old', 'bigger_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch')

    result = diff.create_bindiff_for_files(
        file1=file1, file2=file2, file_patch=file_patch, block_size_in=1,
    )
    assert isinstance(result, dict)
    assert os.path.isfile(file_patch)

    with open(file_patch, 'rb') as fpp:
        assert read_headers(fpp) == {
            '1-mtime': datetime.utcfromtimestamp(os.stat(file1).st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            '2-mtime': datetime.utcfromtimestamp(os.stat(file2).st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            '1-mode': stat.filemode(os.stat(file1).st_mode)[1:],
            '2-mode': stat.filemode(os.stat(file2).st_mode)[1:],
            '1-sha256sum': '4795a1c2517089e4df569afd77c04e949139cf299c87f012b894fccf91df4594',
            '2-sha256sum': 'dc4d8352e3da3129e1c85cb41ffdce1e2a307f308af9d3e1c770d80c5944e01f',
        }

        assert fpp.read() == b'= 3\n\n- 3\n\n456\n\n+ 3\n\nqqq\n\n= 4\n\n- 1\n\n\n\n\n+ 5\n\nabcd\n\n\n'


def test_create_bindiff_for_files_complex_noheaders(data_path, media_path, read_headers):
    file1 = os.path.join(data_path, 'old', 'bigger_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch')

    result = diff.create_bindiff_for_files(
        file1=file1, file2=file2, file_patch=file_patch, block_size_in=1,
        mtime=False, modes=False, hashsums=(),
    )
    assert isinstance(result, dict)
    assert os.path.isfile(file_patch)

    with open(file_patch, 'rb') as fpp:
        assert read_headers(fpp) == {}
        assert fpp.read() == b'= 3\n\n- 3\n\n456\n\n+ 3\n\nqqq\n\n= 4\n\n- 1\n\n\n\n\n+ 5\n\nabcd\n\n\n'


def test_create_bindiff_for_files_unknown_hashes(data_path, media_path, read_headers):
    file1 = os.path.join(data_path, 'old', 'bigger_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch')

    with pytest.raises(ValueError):
        diff.create_bindiff_for_files(
            file1=file1, file2=file2, file_patch=file_patch, block_size_in=1,
            hashsums=('wtfsum',),
        )

    assert not os.path.exists(file_patch)


def test_create_bindiff_for_files_complex_fromempty(data_path, media_path, read_headers):
    file1 = os.path.join(data_path, 'old', 'nonexisting_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch')

    assert not os.path.exists(file1)

    result = diff.create_bindiff_for_files(
        file1=file1, file2=file2, file_patch=file_patch, block_size_in=1,
        allow_empty=True,
        block_size_out=2,  # должен игнорироваться при пустом первом файле
    )
    assert isinstance(result, dict)
    assert os.path.isfile(file_patch)

    with open(file_patch, 'rb') as fpp:
        assert read_headers(fpp) == {
            '1-mtime': datetime(1970, 1, 1, 0, 0, 0).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            '2-mtime': datetime.utcfromtimestamp(os.stat(file2).st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            '1-mode': '---------',
            '2-mode': stat.filemode(os.stat(file2).st_mode)[1:],
            '1-sha256sum': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
            '2-sha256sum': 'dc4d8352e3da3129e1c85cb41ffdce1e2a307f308af9d3e1c770d80c5944e01f',
        }

        assert fpp.read() == b'+ 15\n\n123qqq7890abcd\n\n\n'


def test_create_bindiff_for_files_complex_fromempty_disallowed(data_path, media_path, read_headers):
    file1 = os.path.join(data_path, 'old', 'nonexisting_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch')

    assert not os.path.exists(file1)

    with pytest.raises(OSError):
        diff.create_bindiff_for_files(
            file1=file1, file2=file2, file_patch=file_patch, block_size_in=1,
        )

    assert not os.path.exists(file_patch)


def test_create_bindiff_for_files_complex_gzip_auto(data_path, media_path, read_headers):
    file1 = os.path.join(data_path, 'old', 'bigger_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch.gz')

    result = diff.create_bindiff_for_files(
        file1=file1, file2=file2, file_patch=file_patch, block_size_in=1,
    )
    assert isinstance(result, dict)
    assert os.path.isfile(file_patch)

    with gzip.open(file_patch, 'rb') as fpp:
        # Просто проверяем, что это действительно патч и действительно гзипнутый
        # (корректность содержимого патча уже проверили и перепроверили в тестах выше)
        assert read_headers(fpp)
        assert fpp.read()


def test_create_bindiff_for_files_complex_gzip_auto_fromempty(data_path, media_path, read_headers):
    file1 = os.path.join(data_path, 'old', 'nonexisting_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch.gz')

    result = diff.create_bindiff_for_files(
        file1=file1, file2=file2, file_patch=file_patch, block_size_in=1,
        allow_empty=True,
    )
    assert isinstance(result, dict)
    assert os.path.isfile(file_patch)

    with gzip.open(file_patch, 'rb') as fpp:
        assert read_headers(fpp)
        assert fpp.read()


def test_create_bindiff_for_files_complex_gzip_manual(data_path, media_path, read_headers):
    file1 = os.path.join(data_path, 'old', 'bigger_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch')

    result = diff.create_bindiff_for_files(
        file1=file1, file2=file2, file_patch=file_patch, block_size_in=1,
        gzip_level=9,

    )
    assert isinstance(result, dict)
    assert os.path.isfile(file_patch)

    with gzip.open(file_patch, 'rb') as fpp:
        assert read_headers(fpp)
        assert fpp.read()


def test_create_bindiff_for_files_complex_nogzip_manual(data_path, media_path, read_headers):
    file1 = os.path.join(data_path, 'old', 'bigger_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch.gz')

    result = diff.create_bindiff_for_files(
        file1=file1, file2=file2, file_patch=file_patch, block_size_in=1,
        gzip_level=0,

    )
    assert isinstance(result, dict)
    assert os.path.isfile(file_patch)

    with open(file_patch, 'rb') as fpp:
        # Да-да, мы просили в .gz файл записать НЕ гзип :)
        assert read_headers(fpp)
        assert fpp.read()


#


def test_verbosity(data_path, media_path, read_headers):
    # Просто прогоняем всё с verbose, чтобы проверить, что ничего не упадёт

    file1 = os.path.join(data_path, 'old', 'bigger_file.txt')
    file2 = os.path.join(data_path, 'new', 'bigger_file.txt')
    file_patch = os.path.join(media_path, 'patch.gz')

    diff.create_bindiff_for_files(file1, file2, file_patch, verbose=2)
    diff.create_bindiff_for_files(file1, file2, file_patch, verbose=2, gzip_level=0)
    diff.create_bindiff_for_files(file1 + 'nonexist', file2, file_patch, verbose=2, allow_empty=True)
