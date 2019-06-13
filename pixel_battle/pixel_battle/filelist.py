#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from typing import Any, Optional, List, Dict

from . import utils


def get_argparser_args() -> Dict[str, Any]:
    return {
        "description": "Just prints sliced filelist",
    }


def configure_argparse(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-a", "--abspath", action="store_true", default=False, help="print absolute paths (default: relative to sourcedir)")
    parser.add_argument("--begin", help="begin from this image (relative to sourcedir)")
    parser.add_argument("--end", help="end to this image (relative to sourcedir)")
    parser.add_argument("sourcedir", metavar="SOURCEDIR", help="directory with saved images")


def main(args: argparse.Namespace) -> int:
    sourcedir = os.path.abspath(args.sourcedir)

    # Собираем список всех доступных картинок
    filelist: Optional[List[str]] = utils.find_images(sourcedir)
    assert filelist is not None  # deal with mypy

    # Урезаем его, если попросили
    filelist = utils.slice_filelist(filelist, args.begin, args.end)
    if filelist is None:
        return 1

    print("Processing {} files".format(len(filelist)), file=sys.stderr)
    print("  begin:", filelist[0], file=sys.stderr)
    print("    end:", filelist[-1], file=sys.stderr)

    for f in filelist:
        if args.abspath:
            f = os.path.join(sourcedir, f)
        print(f)

    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(**get_argparser_args())
    configure_argparse(p)
    sys.exit(main(p.parse_args()))
