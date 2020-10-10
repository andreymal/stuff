#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
from typing import Any, Dict


def get_argparser_args() -> Dict[str, Any]:
    return {}


def configure_argparse(parser: argparse.ArgumentParser) -> None:
    from . import grabber, ws, img2video_prepare, img2video, video2img, filelist

    subparsers = parser.add_subparsers(dest="action", help="action")
    subparsers.required = True

    grabber.configure_argparse(
        subparsers.add_parser(name="grabber", **grabber.get_argparser_args())
    )

    ws.configure_argparse(
        subparsers.add_parser(name="ws", **ws.get_argparser_args())
    )

    img2video_prepare.configure_argparse(
        subparsers.add_parser(name="img2video_prepare", **img2video_prepare.get_argparser_args())
    )

    img2video.configure_argparse(
        subparsers.add_parser(name="img2video", **img2video.get_argparser_args())
    )

    video2img.configure_argparse(
        subparsers.add_parser(name="video2img", **video2img.get_argparser_args())
    )

    filelist.configure_argparse(
        subparsers.add_parser(name="filelist", **filelist.get_argparser_args())
    )


def main() -> int:
    parser = argparse.ArgumentParser(**get_argparser_args())
    configure_argparse(parser)

    args = parser.parse_args()

    if args.action == "grabber":
        from . import grabber
        return grabber.main(args)

    if args.action == "ws":
        from . import ws
        return ws.main(args)

    if args.action == "img2video_prepare":
        from . import img2video_prepare
        return img2video_prepare.main(args)

    if args.action == "img2video":
        from . import img2video
        return img2video.main(args)

    if args.action == "video2img":
        from . import video2img
        return video2img.main(args)

    if args.action == "filelist":
        from . import filelist
        return filelist.main(args)

    assert False, "unreachable"


if __name__ == "__main__":
    sys.exit(main())
