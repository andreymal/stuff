#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil

import pytest


_data_path = None
_media_path = None


@pytest.yield_fixture(scope="session", autouse=True)
def cleaner():
    global _data_path, _media_path

    _data_path = os.path.join(os.path.dirname(__file__), 'data')
    _media_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'testmedia')

    os.mkdir(_media_path)

    try:
        yield
    finally:
        shutil.rmtree(_media_path)


@pytest.fixture
def data_path():
    return _data_path


@pytest.yield_fixture(scope="function", autouse=True)
def media_path():
    try:
        yield _media_path
    finally:
        for x in os.listdir(_media_path):
            x = os.path.join(_media_path, x)
            if os.path.isdir(x) and not os.path.islink(x):
                shutil.rmtree(x)
            else:
                os.remove(x)
        assert not os.listdir(_media_path)


@pytest.fixture
def read_headers():
    def read_headers_(fpp, noseek=False):
        if not noseek:
            fpp.seek(0)
        assert fpp.read(13) == b'abindiff 001\n'

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

    return read_headers_
