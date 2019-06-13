#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
from hashlib import sha256
from typing import Optional, Tuple, List

from PIL import Image


last_hash: Tuple[str, str] = None


def calc_image_hash(im: Image.Image, f: str) -> Optional[str]:
    if im.mode != "RGB":
        print("rgb_sha256sum: {}: non-RGB mode".format(f), file=sys.stderr)
        return None
    return sha256(im.tobytes()).hexdigest()


def calc_file_hash(f: str) -> Optional[str]:
    global last_hash

    # Реальный абсолютный путь без симлинков
    abs_f_real = os.path.abspath(os.path.realpath(f))

    # Оптимизация: не пересчитываем ранее посчитанный файл
    # Очень важный частный случай: много симлинков подряд могут ссылаться
    # на одну и ту же картинку, и это заметно ускоряет работу
    if last_hash is not None and last_hash[0] == abs_f_real:
        return last_hash[1]

    h: Optional[str] = None
    try:
        with Image.open(abs_f_real) as im:
            h = calc_image_hash(im, f)  # здесь f только для красоты
        last_hash = (abs_f_real, h)
    except Exception as exc:
        print("rgb_sha256sum: {}: {}".format(f, exc), file=sys.stderr)
    return h


def calc_files(files: List[str]) -> int:
    errors = 0
    for f in files:
        h = calc_file_hash(f)
        if h is None:
            errors += 1
            continue
        print("{}  {}".format(h, f))
        sys.stdout.flush()
    return errors


def check_files(checksum_file: str) -> int:
    errors = 0
    ok_lines = 0
    invalid_lines = 0

    try:
        fp = open(checksum_file, "r")
    except Exception as exc:
        print("rgb_sha256sum: {}: {}".format(checksum_file, exc), file=sys.stderr)
        return 1

    with fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue

            try:
                f1 = line.find(" ")
                if f1 < 0:
                    raise ValueError
                expected_h = line[:f1].lower()
                f = line[f1:].lstrip(" ")
                if len(expected_h) != 64 or not f:
                    raise ValueError
            except Exception:
                invalid_lines += 1
                continue

            ok_lines += 1

            actual_h = calc_file_hash(f)
            if actual_h is None:
                print("{}: FAILED open or read".format(f))
                errors += 1
            elif expected_h == actual_h:
                print("{}: OK".format(f))
            else:
                print("{}: FAILED".format(f))
                errors += 1

    if invalid_lines:
        if not ok_lines:
            print("rgb_sha256sum: {}: no properly formatted SHA256 checksum lines found".format(checksum_file), file=sys.stderr)
        elif invalid_lines == 1:
            print("rgb_sha256sum: {}: 1 line is improperly formatted".format(checksum_file), file=sys.stderr)
        else:
            print("rgb_sha256sum: {}: {} lines are improperly formatted".format(checksum_file, invalid_lines), file=sys.stderr)

    return errors + invalid_lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate sha256sum of rgb image content")
    parser.add_argument("-c", "--check", default=False, action="store_true", help="read SHA256 sums from the FILEs and check them")
    parser.add_argument("files", metavar="FILE", nargs="*", help="Images to read")

    args = parser.parse_args()

    errors = 0
    check_mode = bool(args.check)

    if check_mode:
        for checksum_file in args.files:
            errors += check_files(checksum_file)

    else:
        errors = calc_files(args.files)

    if errors:
        print("rgb_sha256sum: WARNING: there are {} errors".format(errors), file=sys.stderr)

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
