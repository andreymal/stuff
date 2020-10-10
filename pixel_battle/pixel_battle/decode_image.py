#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from datetime import datetime
import typing
from typing import Any, List, Dict, BinaryIO

from PIL import Image

from . import utils


def get_argparser_args() -> Dict[str, Any]:
    return {
        "description": "Decodes single data file to png image",
    }


def configure_argparse(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-p", "--palette", required=True, help="palette file (json)")
    parser.add_argument("input", help="Input file (pixel battle data)")
    parser.add_argument("output", help="Output file (png)")


def main(args: argparse.Namespace) -> int:
    width = 1590
    height = 400

    # Загружаем палитру из файла
    palette = utils.read_palette(args.palette)

    # Загружаем картинку
    with open(args.input, "r", encoding="utf-8-sig") as fp:
        orig_data = fp.read()

    # Код декодирования аналогичен коду в grabber (как-то унести в utils?)
    imglen = width * height
    imgdata = orig_data[:imglen]  # Откусываем JSON-мусор (снежинки) в конце
    metadata = orig_data[imglen:].strip()
    if len(imgdata) < imglen:
        print("WARNING: truncated image!", file=sys.stderr)
        imgdata += "_" * (imglen - len(imgdata))
    elif len(orig_data) > imglen and orig_data[imglen] != "[":
        print("WARNING: unexpected extra data", file=sys.stderr)

    img_rgb = utils.decode_image(imgdata, palette)

    # Сохраняем PNG-файл
    with Image.frombytes("RGB", (width, height), img_rgb) as im:
        im.save(args.output, format="PNG", optimize=True)

    # Копируем дату изменения файла
    st = os.stat(args.input)
    os.utime(args.output, (st.st_atime, st.st_mtime))

    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(**get_argparser_args())
    configure_argparse(p)
    sys.exit(main(p.parse_args()))
