#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import binascii
from hashlib import sha256
from typing import Optional, Union, Set, List, Dict, BinaryIO, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


filename_re = re.compile(r"^([12][0-9]{3})-([01][0-9])-([0-3][0-9])_([0-2][0-9])-([0-6][0-9])-([0-6][0-9])")


def read_palette(path: str) -> Dict[str, bytes]:
    with open(path, "r", encoding="utf-8-sig") as fp:
        data: Dict[str, str] = dict(json.load(fp))
    result: Dict[str, bytes] = {}

    for x, hexcolor in data.items():
        bincolor: bytes = binascii.unhexlify(hexcolor)
        if len(bincolor) != 3:
            raise ValueError("Invalid color {!r}".format(hexcolor))
        if len(x) != 1:
            raise ValueError("Invalid color key {!r}".format(x))
        result[x] = bincolor

    return result


def decode_image(data: str, palette: Dict[str, bytes]) -> bytes:
    unknown_colors: Set[str] = set()

    result = bytearray()
    for x in data:
        c = palette.get(x)
        if c is not None:
            result.extend(c)
        else:
            unknown_colors.add(x)
            result.extend(palette.get("_", b"\xff\x00\xff"))

    if unknown_colors:
        print("WARNING: there are {} unknown colors: {!r}".format(len(unknown_colors), unknown_colors))

    assert len(result) == len(data) * 3
    return bytes(result)


def sha256sum(data: Union[bytes, BinaryIO]) -> str:
    if isinstance(data, bytes):
        return sha256(data).hexdigest()

    h = sha256()
    while True:
        chunk = data.read(65536)
        if not chunk:
            break
        h.update(chunk)
    return h.hexdigest()


def rgb_sha256sum(im: Union[str, "Image.Image"]) -> str:
    from PIL import Image

    if isinstance(im, str):
        with Image.open(im) as im2:
            if im2.mode != "RGB":
                raise ValueError("Non-RGB is not supported")
            return sha256(im2.tobytes()).hexdigest()
    assert isinstance(im, Image.Image)

    if im.mode != "RGB":
        raise ValueError("Non-RGB is not supported")
    return sha256(im.tobytes()).hexdigest()


def get_sleep_time(interval: int = 30) -> float:
    if interval < 1:
        raise ValueError("Invalid interval {}".format(interval))
    tm = time.time()
    tm_to = (int(tm) // int(interval) + 1) * interval
    return max(0.1, float(tm_to - tm))


def find_images(sourcedir: str) -> List[str]:
    """Ищет в каталоге и его подкаталогах все файлы с датой в имени
    и возвращает список путей к ним, отсортированный по именам файлов
    (имена каталогов в сортировке не учитываются).
    """
    sourcedir = os.path.abspath(sourcedir)
    prefix = os.path.join(sourcedir, "")
    assert prefix.endswith(os.path.sep)

    filelist: List[str] = []
    for subpath, _, files in os.walk(sourcedir):
        assert subpath == sourcedir or subpath.startswith(prefix)
        for f in files:
            if not filename_re.search(f):
                continue
            filelist.append(os.path.join(subpath[len(prefix):], f))

    # В именах время, так что сортируем по времени
    filelist.sort(key=lambda x: os.path.split(x)[-1])

    return filelist


def slice_filelist(
    filelist: List[str],
    begin: Optional[str] = None,
    end: Optional[str] = None,
) -> Optional[List[str]]:
    """Из списка файлов, полученного функцией find_images, делает срез
    от первого до последнего указанного файла. Если что-то не нашлось,
    возвращает None.
    """
    if begin:
        try:
            f = filelist.index(begin)
        except ValueError:
            print(begin, "not found!")
            return None
        filelist = filelist[f:]

    if end:
        try:
            f = filelist.index(end)
        except ValueError:
            print(end, "not found!")
            return None
        filelist = filelist[:f + 1]

    if not filelist:
        print("Images not found!")
        return None

    return filelist
