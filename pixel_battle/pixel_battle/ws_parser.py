#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import enum
from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple, Union, BinaryIO, Iterator


MAX_WIDTH = 1590
MAX_HEIGHT = 400
SIZE = MAX_WIDTH * MAX_HEIGHT
MAX_COLOR_ID = 25


class Flag(enum.Enum):
    NONE = 0
    BOMB = 1
    FREEZE = 2
    PIXEL = 3
    FREEZE_CENTER = 4
    RELOAD_CHAT = 5
    BOMB_CENTER = 7
    PIXEL_START = 8
    FLAG_PIXEL = 9


@dataclass
class Pixel:
    x: int
    y: int
    color_index: int
    flag: Flag
    user_id: int = 0
    group_id: int = 0

    @staticmethod
    def parse(data: bytes) -> "Pixel":
        if len(data) != 12:
            raise ValueError("Data length must be 12")

        # В первом байте закодирована информация о закрашенном пикселе
        pxdata = int.from_bytes(data[:4], "little")
        # Во втором байте — id поставившего пиксель пользователя
        user_id = int.from_bytes(data[4:8], "little")
        # В третьем байте — id сообщества, с которого играет пользователь (если без сообщества, то ноль)
        group_id = int.from_bytes(data[8:12], "little")

        meta = pxdata // SIZE
        pos = pxdata - meta * SIZE

        x = pos % MAX_WIDTH
        y = (pos - x) // MAX_WIDTH
        color = meta % MAX_COLOR_ID
        flag = Flag(meta // MAX_COLOR_ID)

        return Pixel(
            x=x,
            y=y,
            color_index=color,
            flag=flag,
            user_id=user_id,
            group_id=group_id,
        )

    @staticmethod
    def parse_many(data: bytes) -> List["Pixel"]:
        result: List["Pixel"] = []

        if len(data) % 12 != 0:
            raise ValueError("Data length must be divisible by 12")

        for i in range(len(data) // 12):
            result.append(Pixel.parse(data[i * 12:i * 12 + 12]))

        return result


def iter_websocket_data(fp: BinaryIO) -> Iterator[Tuple[datetime, Union[str, bytes]]]:
    while True:
        t = fp.read(1)
        if not t:
            break
        assert t in [b"B", b"T"]

        tm = int.from_bytes(fp.read(4), "big")
        usec = int.from_bytes(fp.read(4), "big")
        assert usec < 1000000
        l = int.from_bytes(fp.read(4), "big")
        assert fp.read(1) == b"\n"

        data: Union[str, bytes] = fp.read(l)
        assert fp.read(2) == b"\n\n"

        dt = datetime.utcfromtimestamp(tm)
        dt = dt.replace(microsecond=usec)

        if t == b"T":
            data = data.decode("utf-8")

        yield dt, data
