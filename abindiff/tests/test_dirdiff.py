#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import gzip
import stat
import hashlib
from datetime import datetime

from abindiff import dirdiff


def _sha256sum(fp):
    h = hashlib.sha256()
    while True:
        chunk = fp.read(32768)
        if not chunk:
            break
        h.update(chunk)
    return h.hexdigest()


def _calc_headers(p_old, p_new):
    exist = os.path.exists(p_old)

    if exist:
        with open(p_old, 'rb') as fp:
            h1 = _sha256sum(fp)
    else:
        h1 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    with open(p_new, 'rb') as fp:
        h2 = _sha256sum(fp)

    return {
        '1-mtime': datetime.utcfromtimestamp(os.stat(p_old).st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ') if exist else '1970-01-01T00:00:00.000000Z',
        '2-mtime': datetime.utcfromtimestamp(os.stat(p_new).st_mtime).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        '1-mode': stat.filemode(os.stat(p_old).st_mode)[1:] if exist else '---------',
        '2-mode': stat.filemode(os.stat(p_new).st_mode)[1:],
        '1-sha256sum': h1,
        '2-sha256sum': h2,
    }


def test_dirdiff_complex(data_path, media_path, read_headers):
    input_dir1 = os.path.join(data_path, 'old')
    input_dir2 = os.path.join(data_path, 'new')
    output_dir = os.path.join(media_path, 'patch')

    dirdiff.dirdiff(input_dir1, input_dir2, output_dir, verbose=1)

    assert not os.path.exists(os.path.join(output_dir, 'removed_file.txt.abindiff'))

    for f in (
        'bigger_file.txt', 'created_file.txt', 'smaller_file.txt',
        'unicode_file.txt', 'directory/not_changed_file.txt', 'directory/test.txt'):
        p_old = os.path.join(input_dir1, f)
        p_new = os.path.join(input_dir2, f)
        p = os.path.join(output_dir, f + '.abindiff')

        with open(p, 'rb') as fpp:
            assert read_headers(fpp) == _calc_headers(p_old, p_new)

            if f == 'directory/not_changed_file.txt':
                assert fpp.read() == b'= 12\n\n'
            else:
                assert fpp.read()


def test_dirdiff_complex_gzip(data_path, media_path, read_headers):
    input_dir1 = os.path.join(data_path, 'old')
    input_dir2 = os.path.join(data_path, 'new')
    output_dir = os.path.join(media_path, 'patch')

    dirdiff.dirdiff(input_dir1, input_dir2, output_dir, gzip_level=1, verbose=2)

    assert os.readlink(os.path.join(output_dir, 'symlink.txt')) == os.readlink(os.path.join(input_dir2, 'symlink.txt'))

    assert not os.path.exists(os.path.join(output_dir, 'removed_file.txt.abindiff.gz'))

    for f in (
        'bigger_file.txt', 'created_file.txt', 'smaller_file.txt',
        'unicode_file.txt', 'directory/not_changed_file.txt', 'directory/test.txt'):
        p_old = os.path.join(input_dir1, f)
        p_new = os.path.join(input_dir2, f)
        p = os.path.join(output_dir, f + '.abindiff.gz')

        with gzip.open(p, 'rb') as fpp:
            assert read_headers(fpp) == _calc_headers(p_old, p_new)

            if f == 'directory/not_changed_file.txt':
                assert fpp.read() == b'= 12\n\n'
            else:
                assert fpp.read()
