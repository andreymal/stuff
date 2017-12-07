#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil

import pytest

from abindiff import dirpatch


@pytest.mark.parametrize('mode', ['full', 'short', 'gzip'])
def test_dirpatch_complex(mode, data_path, media_path):
    input_dir = os.path.join(data_path, 'old')
    output_dir = os.path.join(media_path, 'new')
    patch_dir = os.path.join(data_path, 'patch_' + mode)
    reference_dir = os.path.join(data_path, 'new', '')

    dirpatch.dirpatch(input_dir, output_dir, patch_dir, verbose=2)

    for p, _, files in os.walk(reference_dir):
        assert p.startswith(reference_dir)
        p = p[len(reference_dir):]

        for f in files:
            ref_file = os.path.join(reference_dir, p, f)
            actual_file = os.path.join(output_dir, p, f)

            if os.path.islink(ref_file):
                assert os.readlink(ref_file) == os.readlink(actual_file)

            else:
                with open(ref_file, 'rb') as fp:
                    expected_data = fp.read()
                with open(actual_file, 'rb') as fp:
                    actual_data = fp.read()
                    assert expected_data == actual_data
                # TODO: mtime, mode


@pytest.mark.parametrize('mode', ['full', 'gzip'])
def test_dirpatch_complex_revert(mode, data_path, media_path):
    input_dir = os.path.join(data_path, 'new')
    output_dir = os.path.join(media_path, 'old')
    patch_dir = os.path.join(data_path, 'patch_' + mode)
    reference_dir = os.path.join(data_path, 'old', '')

    dirpatch.dirpatch(input_dir, output_dir, patch_dir, revert=True)

    # Откат свежесозданного файла означает его удаление
    assert not os.path.exists(os.path.join(output_dir, 'created_file.txt'))

    # Откат удалённых файлов не реализован
    assert not os.path.exists(os.path.join(output_dir, 'removed_file.txt'))

    for p, _, files in os.walk(reference_dir):
        assert p.startswith(reference_dir)
        p = p[len(reference_dir):]

        for f in files:
            if f == 'removed_file.txt':
                continue
            ref_file = os.path.join(reference_dir, p, f)
            actual_file = os.path.join(output_dir, p, f)

            if os.path.islink(ref_file):
                assert os.readlink(ref_file) == os.readlink(actual_file)

            else:
                with open(ref_file, 'rb') as fp:
                    expected_data = fp.read()
                with open(actual_file, 'rb') as fp:
                    actual_data = fp.read()
                    assert expected_data == actual_data
                # TODO: mtime, mode


@pytest.mark.parametrize('mode', ['full', 'short', 'gzip'])
def test_dirpatch_complex_move(mode, data_path, media_path):
    input_dir = os.path.join(data_path, 'old')
    moved_dir = os.path.join(media_path, 'new_moved')
    output_dir = os.path.join(media_path, 'new')
    patch_dir = os.path.join(data_path, 'patch_' + mode)
    reference_dir = os.path.join(data_path, 'new', '')

    shutil.copytree(input_dir, moved_dir)
    dirpatch.dirpatch(moved_dir, output_dir, patch_dir, move=True)

    assert set(os.listdir(moved_dir)) == {'directory', 'symlink.txt', 'removed_file.txt'}

    for p, _, files in os.walk(reference_dir):
        assert p.startswith(reference_dir)
        p = p[len(reference_dir):]

        for f in files:
            ref_file = os.path.join(reference_dir, p, f)
            actual_file = os.path.join(output_dir, p, f)

            if os.path.islink(ref_file):
                assert os.readlink(ref_file) == os.readlink(actual_file)

            else:
                with open(ref_file, 'rb') as fp:
                    expected_data = fp.read()
                with open(actual_file, 'rb') as fp:
                    actual_data = fp.read()
                    assert expected_data == actual_data
                # TODO: mtime, mode


@pytest.mark.parametrize('mode', ['full', 'gzip'])
def test_dirpatch_complex_move_revert(mode, data_path, media_path):
    return
    input_dir = os.path.join(data_path, 'new')
    moved_dir = os.path.join(media_path, 'old_moved')
    output_dir = os.path.join(media_path, 'old')
    patch_dir = os.path.join(data_path, 'patch_' + mode)
    reference_dir = os.path.join(data_path, 'old', '')

    shutil.copytree(input_dir, moved_dir)
    dirpatch.dirpatch(moved_dir, output_dir, patch_dir, revert=True, move=True)

    assert set(os.listdir(moved_dir)) == {'directory', 'symlink.txt'}

    # Откат свежесозданного файла означает его удаление
    assert not os.path.exists(os.path.join(output_dir, 'created_file.txt'))

    # Откат удалённых файлов не реализован
    assert not os.path.exists(os.path.join(output_dir, 'removed_file.txt'))

    for p, _, files in os.walk(reference_dir):
        assert p.startswith(reference_dir)
        p = p[len(reference_dir):]

        for f in files:
            if f == 'removed_file.txt':
                continue
            ref_file = os.path.join(reference_dir, p, f)
            actual_file = os.path.join(output_dir, p, f)

            if os.path.islink(ref_file):
                assert os.readlink(ref_file) == os.readlink(actual_file)

            else:
                with open(ref_file, 'rb') as fp:
                    expected_data = fp.read()
                with open(actual_file, 'rb') as fp:
                    actual_data = fp.read()
                    assert expected_data == actual_data
                # TODO: mtime, mode
