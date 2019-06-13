#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Any, Optional, List, Dict, TextIO

from PIL import Image, ImageFont, ImageDraw

from . import utils


class ImageProcessor:
    def __init__(
        self,
        font: str,
        font_size: int,
        font_antialias: bool = True,
        bgcolor: Any = (0, 0, 0),
        fontcolor: Any = (255, 255, 255),
        label_format: str = "%Y-%m-%d %H:%M:%S MSK",
    ):
        self.font = ImageFont.truetype(font, font_size)
        self.line_height = sum(self.font.getmetrics())
        self.font_antialias = bool(font_antialias)
        self.bgcolor = bgcolor
        self.fontcolor = fontcolor
        self.label_format = label_format

    def process(
        self,
        srcim: Image.Image,
        dt: datetime,
        label: Optional[str] = None,
    ) -> Image.Image:
        new_w = srcim.size[0]
        new_h = srcim.size[1] + self.line_height

        # H.264 требует чётных размеров картинки, фиксим если надо
        new_w += new_w % 2
        new_h += new_h % 2

        im = Image.new("RGB", (new_w, new_h), self.bgcolor)
        with srcim.convert("RGB") as cnv:
            im.paste(cnv, (0, 0))

        if label is None:
            label = dt.strftime(self.label_format)

        draw = ImageDraw.Draw(im)
        if not self.font_antialias:
            draw.fontmode = "1"
        draw.text((2, im.size[1] - self.line_height), label, fill=self.fontcolor, font=self.font)

        return im


def get_argparser_args() -> Dict[str, Any]:
    return {
        "description": "Prepares saved VK Pixel Battle images for video",
    }


def configure_argparse(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-c", "--concat", help="ffconcat output path")
    parser.add_argument("-O", "--optimize", default=False, action="store_true", help="optimize PNG")
    parser.add_argument("-f", "--force", default=False, action="store_true", help="recreate already existing dest files")
    parser.add_argument("-A", "--noantialias", default=False, action="store_true", help="disable font antialiasing")
    parser.add_argument("--begin", help="begin from this image (relative to sourcedir)")
    parser.add_argument("--end", help="end to this image (relative to sourcedir)")
    parser.add_argument("--font", help="font (default: arial.ttf)", default="arial.ttf")
    parser.add_argument("-fs", "--fontsize", type=int, help="font size (default: 20)", default=20)
    parser.add_argument("--extra", help="JSON file with extra configuration")
    parser.add_argument("sourcedir", metavar="SOURCEDIR", help="directory with saved images")
    parser.add_argument("destdir", metavar="DESTDIR", help="destination")


def main(args: argparse.Namespace) -> int:
    sourcedir = os.path.abspath(args.sourcedir)
    destdir = os.path.abspath(args.destdir)
    concat_path: Optional[str] = os.path.abspath(args.concat) if args.concat else None

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
    # {"1970-01-01_00/1970-01-01_00-00-00.png": "Нестандартный лейбл вместо обычной даты"}
    extra_labels: Dict[str, str] = extra.get("labels") or {}

    # Собираем список всех доступных картинок
    filelist: Optional[List[str]] = utils.find_images(sourcedir)
    assert filelist is not None

    # Урезаем его, если попросили
    filelist = utils.slice_filelist(filelist, args.begin, args.end)
    if filelist is None:
        return 1

    print("Processing {} files".format(len(filelist)))
    print("  begin:", filelist[0])
    print("    end:", filelist[-1])

    # Инициализируем обрабатывалку
    processor = ImageProcessor(
        font=args.font,
        font_size=args.fontsize,
        font_antialias=not args.noantialias,
    )

    if not os.path.isdir(destdir):
        os.makedirs(destdir)

    concat_fp: Optional[TextIO] = open(concat_path, "w", encoding="utf-8") if concat_path else None

    try:
        if concat_fp:
            concat_fp.write("ffconcat version 1.0\n\n")

        for i, relsrcpath in enumerate(filelist):
            # Сборка и проверка путей
            srcpath = os.path.join(sourcedir, relsrcpath)
            relsrcpath = relsrcpath.replace(os.path.sep, "/")

            filename = os.path.split(srcpath)[1]
            print("[{}/{}]".format(i + 1, len(filelist)), filename, end="... ", flush=True)

            assert filename.endswith(".png")  # TODO: расхардкодить, может?
            day, tm = filename[:len("0000-00-00_00-00-00")].split("_")
            dt = datetime.strptime(day + " " + tm, "%Y-%m-%d %H-%M-%S")

            skip = False

            dstdirpath = os.path.join(destdir, day + "_" + tm[:2])
            dstpath = os.path.join(dstdirpath, filename)

            # Если готовый файл существует, то делать нечего
            if os.path.exists(dstpath):
                if not args.force:
                    print("exists, skipped;", end=" ")
                    skip = True
            elif not os.path.isdir(dstdirpath):
                os.makedirs(dstdirpath)

            # Для concat файла
            reldstpath: Optional[str] = None
            if concat_fp is not None:
                assert concat_path is not None
                reldstpath = os.path.relpath(dstpath, start=os.path.dirname(concat_path))
                reldstpath = reldstpath.replace(os.path.sep, "/")

            if not skip:
                # Обрабатываем
                with Image.open(srcpath) as srcim:
                    dstim = processor.process(srcim, dt, label=extra_labels.get(relsrcpath))

                # Сохраняем обработанное
                # (если процесс сохранения будет прерван, то недописанный
                # файл обязательно удаляем)
                try:
                    with dstim:
                        dstim.save(dstpath, format="PNG", optimize=args.optimize)
                except:
                    if os.path.isfile(dstpath):
                        print("rm broken file")
                        os.remove(dstpath)
                    raise

            # Пишем информацию в плейлист
            if concat_fp is not None:
                assert reldstpath is not None  # deal with mypy
                for _ in range(extra_duration.get(relsrcpath, 1)):
                    concat_fp.write('file "{}"\n'.format(reldstpath.replace('"', '\\"')))

            print("ok.")

    finally:
        if concat_fp is not None:
            concat_fp.close()
            concat_fp = None

    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(**get_argparser_args())
    configure_argparse(p)
    sys.exit(main(p.parse_args()))
