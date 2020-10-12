#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from typing import Any, Dict

from . import utils


def get_argparser_args() -> Dict[str, Any]:
    return {
        "description": "Just prints sliced filelist",
    }


def configure_argparse(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-a", "--abspath", action="store_true", default=False, help="print absolute paths (default: relative to sourcedir)")
    parser.add_argument("--begin", help="begin from this image (relative to sourcedir)")
    parser.add_argument("--end", help="end to this image (relative to sourcedir)")
    parser.add_argument("--extra", help="JSON file with extra durations")
    parser.add_argument("sourcedir", metavar="SOURCEDIR", help="directory with saved images")


def main(args: argparse.Namespace) -> int:
    sourcedir = os.path.abspath(args.sourcedir)

    # Загружаем extra конфиг из json-файла
    extra: Dict[str, Any] = {}
    if args.extra:
        with open(args.extra, "r", encoding="utf-8-sig") as fp:
            extra = json.load(fp)
            if not isinstance(extra, dict):
                print("Invalid extra file")
                return 1

    # {"1970-01-01_00/1970-01-01_00-00-00.png": 777 число повторов этого кадра если надо}
    extra_duration: Dict[str, int] = extra.get("duration") or {}

    # Собираем список всех доступных картинок
    filelist_full = utils.find_images(sourcedir)

    # Урезаем его, если попросили
    filelist = utils.slice_filelist(filelist_full, args.begin, args.end)
    if filelist is None:
        return 1

    print("Processing {} files".format(len(filelist)), file=sys.stderr)
    print("  begin:", filelist[0], file=sys.stderr)
    print("    end:", filelist[-1], file=sys.stderr)

    for f in filelist:
        f_ready = f
        if args.abspath:
            f_ready = os.path.abspath(os.path.join(sourcedir, f))
        for _ in range(extra_duration.get(f, 1)):
            print(f_ready)

    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(**get_argparser_args())
    configure_argparse(p)
    sys.exit(main(p.parse_args()))
