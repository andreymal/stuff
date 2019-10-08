#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import shlex
import argparse
from subprocess import Popen, PIPE
from typing import Any, Optional, List, Dict

from PIL import Image

from . import utils


def get_argparser_args() -> Dict[str, Any]:
    return {
        "description": "Converts video file (typically lossless RGB) back to Pixel Battle PNG images.",
    }


def configure_argparse(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-f", "--force", default=False, action="store_true", help="override existing files")
    parser.add_argument("--use-symlinks", default=False, action="store_true", help="Use symlinks to deduplicate files")
    parser.add_argument("-s", "--size", help="source video size (default: 1590x400)", default="1590x400")
    parser.add_argument("--begin", help="begin from this image (relative to sourcedir)")
    parser.add_argument("--end", help="end to this image (relative to sourcedir)")
    parser.add_argument("--ext", help="override files extension (default: read from filelist)")
    parser.add_argument("--crop", help="crop rect (ffmpeg filter syntax: width:height:x:y)")
    parser.add_argument("-F", "--saveopts", help="save options for PIL.Image.save (JSON, default: auto)")
    parser.add_argument("--ffmpeg", help="customize ffmpeg command", default="ffmpeg -hide_banner -loglevel error")
    parser.add_argument("filelist", metavar="FILELIST", help="file list filename")
    parser.add_argument("source", metavar="SOURCE", help="source video file")
    parser.add_argument("destdir", metavar="DESTDIR", help="destination directory")


def main(args: argparse.Namespace) -> int:
    saveopts: Optional[Dict[str, Any]] = None
    if args.saveopts is not None:
        saveopts = json.loads(args.saveopts)

    if saveopts is not None and not isinstance(saveopts, dict):
        raise ValueError

    w: int
    h: int
    try:
        w, h = [int(x) for x in args.size.split("x", 1)]
    except Exception:
        print("Cannot parse video size")
        return 1

    crop: Optional[str] = str(args.crop) if args.crop else None
    if crop:
        for c in " ,;'\"=":  # Просто защита от дурака
            if c in crop:
                print("Invalid crop value")
                return 1

    destdir = os.path.abspath(args.destdir)
    destdir = os.path.join(destdir, "")  # add "/" postfix
    # if not args.force and os.path.exists(destdir) and os.listdir(destdir):
    #     print("{!r} already exists".format(destdir))
    #     return 1

    # Загружаем список кадров из файла
    filelist: List[str] = []
    with open(args.filelist, "r", encoding="utf-8-sig") as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if not os.path.join(destdir, line).startswith(destdir):
                print("Unsafe path: {!r}".format(line))
                return 1
            filelist.append(line)

    # Урезаем
    skip_frames = 0

    if args.begin:
        try:
            f = filelist.index(args.begin)
        except ValueError:
            print(args.begin, "not found!")
            return 1
        filelist = filelist[f:]
        skip_frames = f

    if args.end:
        try:
            f = filelist.index(args.end)
        except ValueError:
            print(args.end, "not found!")
            return 1
        filelist = filelist[:f + 1]

    # Превращаем его в стек
    filelist.reverse()

    # Видеофильтры (обрезка)
    video_filters: List[str] = []

    if crop:
        video_filters.append("crop={}".format(crop))

    # Собираем команду ffmpeg
    ffmpeg_cmd: List[str] = list(shlex.split(args.ffmpeg))

    # Эта опция предотвращает появление дубликатов кадров, если в исходном
    # видео частота кадров переменная
    ffmpeg_cmd += ["-vsync", "passthrough"]

    ffmpeg_cmd += [
        "-i", os.path.abspath(args.source),
        "-pix_fmt", "rgb24",
    ]
    if video_filters:
        ffmpeg_cmd.extend(["-vf", ",".join(video_filters)])
    ffmpeg_cmd += [
        "-f", "rawvideo",
        "pipe:1",
    ]

    # Создаём нужные переменные для работы с ffmpeg
    ffmpeg: Optional[Popen] = None
    prev_rgb_hash = ""
    prev_fileabspath = ""
    frameno = -1

    # Вот по столько байт на кадр будет нам выдавать ffmpeg
    frame_len = w * h * 3  # bytes

    try:
        # Запускаем ffmpeg
        ffmpeg = Popen(
            ffmpeg_cmd,
            shell=False,
            stdin=PIPE,
            stdout=PIPE,
        )

        while True:
            # Читаем по одному кадру из ffmpeg
            framedata = ffmpeg.stdout.read(frame_len)
            if not framedata:
                if not filelist:
                    break
                print("Missing {} frames!".format(len(filelist)))
                return 1

            if len(framedata) != frame_len:
                print("Truncated input from ffmpeg (maybe incorrect video size?)")
                return 1

            if not filelist:
                if args.end:
                    break
                print("Unexpected extra frame from ffmpeg!")
                return 1

            frameno += 1
            if frameno < skip_frames:
                continue

            # Забираем название этого файла из нашего типа-стека
            filepath = filelist.pop()
            if args.ext:
                filepath = os.path.splitext(filepath)[0]
                filepath = filepath + "." + str(args.ext).lstrip(".")
                ext = args.ext.lower()
            else:
                ext = os.path.splitext(filepath)[1].lower().lstrip(".")
            print(filepath, end="", flush=True)

            rgb_hash = utils.sha256sum(framedata)

            fileabspath = os.path.join(destdir, filepath)

            # Кодируем с помщью Pillow и сохраняем, если его ещё не существует
            if args.force or not os.path.exists(fileabspath):
                fileabsdir = os.path.dirname(fileabspath)
                if not os.path.exists(fileabsdir):
                    os.makedirs(fileabsdir)

                # Если разрешают делать симлинки, то делаем, если кадр такой же
                if args.use_symlinks and rgb_hash == prev_rgb_hash:
                    assert prev_fileabspath
                    link_to = os.path.relpath(prev_fileabspath, os.path.dirname(fileabspath))
                    os.symlink(link_to, fileabspath)

                else:
                    file_saveopts = saveopts
                    if file_saveopts is None:
                        if ext == "gif":
                            file_saveopts = {"format": "GIF"}
                        elif ext == "png":
                            file_saveopts = {"format": "PNG", "optimize": True}
                        elif ext in ("jpeg", "jpg", "jpe"):
                            file_saveopts = {"format": "JPEG", "quality": 100}
                        elif ext == "webp":
                            file_saveopts = {"format": "WEBP"}
                        else:
                            file_saveopts = {"format": "BMP"}
                    assert file_saveopts is not None

                    with Image.frombytes("RGB", (w, h), framedata) as img:
                        img.save(fileabspath, **file_saveopts)
                    prev_rgb_hash = rgb_hash
                    prev_fileabspath = fileabspath

            print("", flush=True)

        try:
            ffmpeg.stdin.write(b"q")
            ffmpeg.stdin.close()
        except Exception:
            pass

        # Нужно прочитать остатки stdout, иначе ffmpeg переполнит буфер
        # и зависнет
        while True:
            if not ffmpeg.stdout.read(frame_len):
                break

        # Смотрим, как отработал ffmpeg
        code = ffmpeg.wait()
        ffmpeg = None
        if code != 0:
            print("Error: ffmpeg exited with code {}".format(code))
            return code

    finally:
        if ffmpeg is not None:
            try:
                ffmpeg.stdin.write(b"q")
                ffmpeg.stdin.close()

                # Нужно прочитать остатки stdout, иначе ffmpeg переполнит буфер
                # и зависнет
                while True:
                    if not ffmpeg.stdout.read(frame_len):
                        break

                ffmpeg.wait(timeout=1)
            except Exception:
                pass

            try:
                ffmpeg.terminate()
            except Exception:
                pass
            ffmpeg.wait(timeout=10)

    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(**get_argparser_args())
    configure_argparse(p)
    sys.exit(main(p.parse_args()))
