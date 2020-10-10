#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from datetime import datetime
import typing
from typing import Any, List, Dict, BinaryIO

if typing.TYPE_CHECKING:
    import websockets


def get_argparser_args() -> Dict[str, Any]:
    return {
        "description": "Saves received data from websocket to file",
    }


def configure_argparse(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", required=True, help="Websocket URL")
    parser.add_argument("-o", "--output", required=True, help="Output file")


async def ws_grab(ws: "websockets.client.WebSocketClientProtocol", fp: BinaryIO):
    while True:
        data = await ws.recv()
        data_bin = data.encode("utf-8") if isinstance(data, str) else data
        dt = datetime.utcnow()
        print(dt.strftime("%Y-%m-%d %H:%M:%S"), len(data_bin), flush=True)

        # Формат записываемого файла такой:
        # - буква T или B — если пришли текстовые или бинарные данные соответственно;
        # - 4 байта — время получения в секундах;
        # - 4 байта — микросекунды;
        # - 4 байта — длина полученных данных в байтах (если текст, то кодировка utf-8);
        # - символ переноса строки;
        # - собственно данные;
        # - два переноса строки как признак окончания куска данных.
        buf: List[bytes] = [b"T" if isinstance(data, str) else b"B"]
        buf.append(int(dt.timestamp()).to_bytes(4, "big"))
        buf.append(dt.microsecond.to_bytes(4, "big"))
        buf.append(len(data_bin).to_bytes(4, "big"))
        buf.append(b"\n")
        buf.append(data_bin)
        buf.append(b"\n\n")

        fp.write(b"".join(buf))


async def async_main(args: argparse.Namespace) -> int:
    import websockets

    async with websockets.connect(args.url) as ws:
        with open(args.output, "ab") as fp:
            await ws_grab(ws, fp)


def main(args: argparse.Namespace) -> int:
    import asyncio
    asyncio.run(async_main(args))
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(**get_argparser_args())
    configure_argparse(p)
    sys.exit(main(p.parse_args()))
