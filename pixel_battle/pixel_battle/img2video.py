#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import shlex
import argparse
from subprocess import Popen, PIPE
from typing import Any, Optional, List, Dict, TextIO

from . import utils


def get_argparser_args() -> Dict[str, Any]:
    return {
        "description": "Converts Pixel Battle PNG images to H264/VP9 YUV/RGB video",
    }


def configure_argparse(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-c", "--concat", help="ffconcat output filename")
    parser.add_argument("-l", "--list", help="file list output filename")
    parser.add_argument("--force", default=False, action="store_true", help="override existing files")
    parser.add_argument("-ir", "--input-fps", type=int, help="input video framerate (default: 30)", default=30)
    parser.add_argument("-or", "--output-fps", type=int, help="output video framerate (default: same as input)", default=0)
    parser.add_argument("-g", "--keyint", type=int, help="keyframe interval (default: fps*5)", default=0)
    parser.add_argument("--begin", help="begin from this image (relative to sourcedir)")
    parser.add_argument("--end", help="end to this image (relative to sourcedir)")
    parser.add_argument("--ffmpeg", help="customize ffmpeg command", default="ffmpeg -hide_banner")
    parser.add_argument("--crop", help="crop rect (ffmpeg filter syntax: width:height:x:y)")
    parser.add_argument("--scale", help="scale video after grop (Nx without antialiasing (e.g. 2x) or ffmpeg filter syntax)")
    parser.add_argument("-p", "--pixfmt", help="Pixel format (default: rgb24)", default="rgb24", choices=[
        "rgb24",
        "gbrp",
        "yuv420p",
        "yuv422p",
        "yuv444p",
        "yuvj420p",
        "yuvj422p",
        "yuvj444p",
    ])
    parser.add_argument("--format", help="Video output format (default: vp9)", default="vp9", choices=[
        "vp9",
        "h264",
        "h264-main",
        "h264-baseline",
        "custom",
    ])
    parser.add_argument("--extra-args", help="ffmpeg output arguments (useful with the custom video format)", default=None)
    parser.add_argument("-b", "--bitrate", help="bitrate (only for lossy formats)", default=None)
    parser.add_argument("-crf", help="crf (only for lossy h264)", default=None)
    parser.add_argument("--print-ffmpeg", default=False, action="store_true", help="just print ffmpeg command and exit")
    parser.add_argument("--extra", help="JSON file with extra configuration")
    parser.add_argument("sourcedir", metavar="SOURCEDIR", help="directory with saved images")
    parser.add_argument("dest", metavar="DEST", help="destination file")


def main(args: argparse.Namespace) -> int:
    sourcedir = os.path.abspath(args.sourcedir)
    dest = os.path.abspath(args.dest)
    concat_path: Optional[str] = os.path.abspath(args.concat) if args.concat else None
    list_path: Optional[str] = os.path.abspath(args.list) if args.list else None
    pixfmt = args.pixfmt

    # Проверка адекватности аргументов
    if args.format in ("h264-main", "h264-baseline") and pixfmt not in ("yuv420p", "yuvj420p"):
        print("{} can be used only with yuv420p pixel format".format(args.format))
        return 1
    if pixfmt in ("rgb24",) and args.format not in ("custom", "vp9", "h264"):
        print("{} pixel format is available only for lossless formats (vp9, h264), not {}".format(
            pixfmt, args.format
        ))
        return 1
    if args.bitrate and args.crf:
        print("--bitrate and --crf cannot be used together")
        return 1

    crop: Optional[str] = str(args.crop) if args.crop else None
    if crop:
        for c in " ,;'\"=":  # Просто защита от дурака
            if c in crop:
                print("Invalid crop value")
                return 1

    scale: Optional[str] = str(args.scale) if args.scale else None
    if scale is not None:
        if scale.endswith("x") and scale[:-1].isdigit:
            scale = "iw*{0}:ih*{0}:flags=neighbor".format(scale[:-1])
        else:
            for c in " ,;'\"":  # Просто защита от дурака
                if c in scale:
                    print("Invalid scale value")
                    return 1

    # Преобразуем pixfmt в совместимый если надо
    if args.format == "vp9" and pixfmt == "rgb24":
        pixfmt = "gbrp"

    keyint = int(args.keyint)
    if not keyint:
        keyint = (args.output_fps or args.input_fps) * 5

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

    if not args.force and not args.print_ffmpeg:
        for pt in [dest, concat_path, list_path]:
            if not pt:
                continue
            if os.path.exists(pt):
                print("{!r} already exists".format(pt))
                return 1

    # Собираем список всех доступных картинок
    filelist_full = utils.find_images(sourcedir)

    # Урезаем его, если попросили
    filelist = utils.slice_filelist(filelist_full, args.begin, args.end)
    if filelist is None:
        return 1

    if not args.print_ffmpeg:
        print("Processing {} files".format(len(filelist)))
        print("  begin:", filelist[0])
        print("    end:", filelist[-1])

    # Собираем аргументы для запуска ffmpeg
    ffmpeg_args: List[str] = list(shlex.split(args.ffmpeg))

    # Так предотвращается самовольное изменение частоты кадров ffmpeg'ом,
    # если она у входящего видео например переменная (у нас она не переменная,
    # но пусть будет на всякий случай)
    ffmpeg_args.extend(["-vsync", "passthrough"])

    # Параметры входящего видео (будем пихать ffconcat в stdin)
    ffmpeg_input_args = [
        "-safe", "0",
        "-protocol_whitelist", "file,pipe",
        # Одновременно с duration указывать не нужно, но приходится,
        # потому что стандартный time base 1/25 не дружит с 30fps
        "-r", str(args.input_fps),
        "-f", "concat",
        "-i", "pipe:0",
    ]

    # Параметры обработки видео
    ffmpeg_filter_args: List[str] = []
    video_filters: List[str] = []

    if args.format != "custom":
        # Если не кастом, конвертируем формат пикселя в нужный
        ffmpeg_filter_args.extend(["-pix_fmt", pixfmt])
        # И меняем выходной fps
        if args.output_fps > 0 and args.output_fps != args.input_fps:
            video_filters.append("fps=fps={}".format(args.output_fps or args.input_fps))

    if crop:
        video_filters.append("crop={}".format(crop))
    if scale:
        video_filters.append("scale={}".format(scale))

    if video_filters:
        ffmpeg_filter_args.extend(["-vf", ",".join(video_filters)])

    # Параметры кодирования видео и упаковки его в контейнер
    ffmpeg_video_args: List[str] = []
    ffmpeg_output_args: List[str] = []

    if args.format == "vp9":
        # VP9 Lossless
        ffmpeg_video_args.extend([
            "-c:v", "libvpx-vp9",
            "-lossless", "1",
            "-deadline", "good",
            "-cpu-used", "0",
            "-g", str(keyint),
        ])
        ffmpeg_output_args.extend([
            "-f", "webm",
        ])

    elif args.format == "h264":
        # H.264 Lossless
        ffmpeg_video_args.extend([
            "-c:v", "libx264rgb" if pixfmt in ("rgb24", "gbrp") else "libx264",
            "-preset", "veryslow",
            "-crf", "0",
            "-g", str(keyint),
            "-x264opts", "no-scenecut",
        ])
        ffmpeg_output_args.extend([
            "-f", "mp4",
            "-movflags", "+faststart",
        ])

    elif args.format == "h264-main":
        # H.264 Lossy Main
        ffmpeg_video_args.extend([
            "-c:v", "libx264",
            "-profile:v", "main",
            "-level", "4.1",
            "-preset", "slow",
            "-g", str(keyint),
            "-x264opts", "no-scenecut",
        ])
        ffmpeg_output_args.extend([
            "-f", "mp4",
            "-movflags", "+faststart",
        ])
        if args.bitrate:
            ffmpeg_video_args.extend(["-b:v", args.bitrate])
        if args.crf:
            ffmpeg_video_args.extend(["-crf", args.crf])

    elif args.format == "h264-baseline":
        # H.264 Lossy Baseline, чтобы в чатики телеграма кидать
        ffmpeg_video_args.extend([
            "-c:v", "libx264",
            "-profile:v", "baseline",
            "-level", "3.1",
            "-preset", "slow",
            "-tune", "fastdecode",
            "-g", str(keyint),
            "-x264opts", "no-scenecut",
        ])
        ffmpeg_output_args.extend([
            "-f", "mp4",
            "-movflags", "+faststart",
        ])
        if args.bitrate:
            ffmpeg_video_args.extend(["-b:v", args.bitrate])
        if args.crf:
            ffmpeg_video_args.extend(["-crf", args.crf])

    else:
        # Если кастом, пользователь напишет аргументы сам
        assert args.format == "custom"

    if args.extra_args:
        ffmpeg_video_args.extend(shlex.split(args.extra_args))

    # Выходной файл
    # (обратите внимание, что расширение файла не обязано соответствовать
    # реальному формату видео)
    ffmpeg_output_args.extend(["-y", dest])

    # Собираем всё в одну кучу
    ffmpeg_args.extend(ffmpeg_input_args)
    ffmpeg_args.extend(ffmpeg_filter_args)
    ffmpeg_args.extend(ffmpeg_video_args)
    ffmpeg_args.extend(ffmpeg_output_args)

    # Если просили только отпечатать аргументы, то печатаем и валим
    if args.print_ffmpeg:
        print(" ".join(shlex.quote(x) for x in ffmpeg_args))
        return 0

    concat_fp: Optional[TextIO] = None
    list_fp: Optional[TextIO] = None
    ffmpeg: Optional[Popen] = None
    dur = 1.0 / args.input_fps
    try:
        # Файлы со списком кадров
        if concat_path:
            concat_fp = open(concat_path, "w", encoding="utf-8", newline="")
        if list_path:
            list_fp = open(list_path, "w", encoding="utf-8", newline="")

        # Запускаем сам ffmpeg
        ffmpeg = Popen(
            ffmpeg_args,
            shell=False,
            stdin=PIPE,
            bufsize=0,  # отключаем буферизацию stdin
        )
        assert ffmpeg is not None  # mypy hint

        ffmpeg.stdin.write(b"ffconcat version 1.0\n\n")
        if concat_fp:
            concat_fp.write("ffconcat version 1.0\n\n")

        # Пишем пути к картинкам в ffmpeg и в файлы
        for filepath in filelist:
            fileabspath = os.path.join(sourcedir, filepath)
            assert "'" not in fileabspath
            for _ in range(extra_duration.get(filepath, 1)):
                ffmpeg.stdin.write(b"file 'file:" + fileabspath.encode("utf-8") + b"'\n")
                # Хотя указание duration необязательно, с ним ffmpeg меньше плющит в логах
                # (и этот duration всё равно игнорируется из-за -r выше)
                ffmpeg.stdin.write(b"duration " + str(dur).encode("utf-8") + b"\n")

                if concat_fp is not None:
                    concat_fp.write("file 'file:" + filepath + "'\n")
                if list_fp is not None:
                    list_fp.write(filepath + "\n")

        if concat_fp is not None:
            concat_fp.flush()
        if list_fp is not None:
            list_fp.flush()

        ffmpeg.stdin.close()

        # Смотрим, как отработал ffmpeg
        code = ffmpeg.wait()
        ffmpeg = None
        if code != 0:
            print("Error: ffmpeg exited with code {}".format(code))
            return code

    finally:
        # Прибираем за собой
        if concat_fp is not None:
            concat_fp.close()
            concat_fp = None
        if list_fp is not None:
            list_fp.close()
            list_fp = None

        if ffmpeg is not None:
            try:
                ffmpeg.stdin.close()
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
