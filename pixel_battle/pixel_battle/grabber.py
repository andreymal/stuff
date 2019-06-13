#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import argparse
import traceback
from io import BytesIO
from datetime import datetime
from urllib.request import Request, urlopen
from typing import Any, Optional, List, Dict, TextIO
import dataclasses
from dataclasses import dataclass

from PIL import Image

from . import utils


default_url = "http://pixel.vkforms.ru/data/1.bmp"
user_agent = "Mozilla/5.0; pixel_battle/0.3 (grabber; https://github.com/andreymal/stuff/tree/master/pixel_battle)"
log_fp: Optional[TextIO] = None


@dataclass
class PixelBattleState:
    last_image: Optional[str] = None  # Никогда не бывает симлинком, а путь всегда относительный
    last_rgb_sha256sum: Optional[str] = None
    last_symlinks: List[str] = dataclasses.field(default_factory=list)  # Список относительных путей

    def clear_last(self) -> None:
        self.last_image = None
        self.last_rgb_sha256sum = None
        self.last_symlinks.clear()


    def validate_last_image(self, root: str) -> None:
        if not self.last_image:
            self.clear_last()
            return

        last_image = os.path.join(root, self.last_image)
        if not os.path.isfile(last_image) or os.path.islink(last_image):
            self.clear_last()
            log("Last image {!r} not found, ignored".format(last_image))
            return

        try:
            h = utils.rgb_sha256sum(last_image)
        except Exception:
            self.clear_last()
            log("Last image {!r} cannot be read, ignored".format(last_image))
            return

        if h != self.last_rgb_sha256sum:
            self.clear_last()
            log("Last image {!r} was changed, ignored".format(last_image))

    def validate(self, root: str) -> None:
        self.validate_last_image(root)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(dataclasses.asdict(self), fp, ensure_ascii=False, sort_keys=True, indent=2)


state = PixelBattleState()


def download(
    url: str,
    maxsize: int = 5 * 1024 * 1024,
    tries: int = 3,
    tries_interval: float = 1.5,
) -> Optional[bytes]:
    # Готовим HTTP-запрос
    r = Request(url)
    r.add_header("User-Agent", user_agent)

    log("grab...", tm=False, end=" ")

    # Пытаемся скачать в три попытки, а то иногда бывает ошибка 502
    data = b""
    for trynum in range(tries):
        try:
            data = urlopen(r, timeout=10).read(maxsize + 1)
        except Exception as exc:
            log(str(exc), tm=False, end=" ")
            if trynum >= tries - 1:
                return None
        else:
            break
        time.sleep(tries_interval)

    if len(data) > maxsize:
        log("(image size is too big, it will be truncated!)", tm=False, end=" ")
        data = data[:maxsize]

    return data


def grab(
    url: str,
    root: str,
    maxsize: int = 5 * 1024 * 1024,
    use_symlinks: bool = False,
    filename: Optional[str] = None,
    filename_format: str = "%Y-%m-%d_%H/%Y-%m-%d_%H-%M-%S.png",
    filename_utc: bool = False,
    saveopts: Optional[Dict[str, Any]] = None,
    last_filename: Optional[str] = "last.png",
    json_filename: Optional[str] = "last.json",
) -> None:
    # Генерируем имя сохраняемой картинки
    tm = datetime.utcnow()  # UTC
    tm_local = datetime.now()  # local timezone
    if not filename:
        if filename_utc:
            filename = tm.strftime(filename_format)
        else:
            filename = tm_local.strftime(filename_format)

    # Определяемся с форматом сохраняемой картинки
    ext = os.path.splitext(filename)[-1].lower().lstrip(".")
    if saveopts is None:
        if ext == "gif":
            saveopts = {"format": "GIF"}
        elif ext == "png":
            saveopts = {"format": "PNG", "optimize": True}
        elif ext in ("jpeg", "jpg", "jpe"):
            saveopts = {"format": "JPEG", "quality": 100}
        elif ext == "webp":
            saveopts = {"format": "WEBP"}
        else:
            saveopts = {"format": "BMP"}
    assert saveopts is not None

    orig_data: Optional[bytes] = download(url, maxsize)
    if orig_data is None:
        log("fail!", tm=False)
        return

    log("save...", tm=False, end=" ")

    symlink_to: Optional[str] = None
    data = b""
    file_hash = ""

    with Image.open(BytesIO(orig_data)) as im:
        if im.mode != "RGB":
            raise NotImplementedError("Unsupported image mode: {!r}".format(im.mode))

        # Считаем хэш содержимого (не bmp-файла, а именно содержимого пикселей в RGB)
        rgb_hash = utils.rgb_sha256sum(im)

        if (
            use_symlinks and state.last_rgb_sha256sum == rgb_hash and
            state.last_image and os.path.isfile(os.path.join(root, state.last_image))
        ):
            # Если такая картинка уже есть, то просто делаем симлинк на неё
            symlink_to = state.last_image
            # TODO: неоптимально же каждый раз хэш считать
            with open(os.path.join(root, symlink_to), "rb") as fp:
                file_hash = utils.sha256sum(fp)

        else:
            # Если нет — сохраняем файл
            data1 = BytesIO()
            im.save(data1, **saveopts)
            data = data1.getvalue()
            file_hash = utils.sha256sum(data)

    # Создаём каталог под картинку
    path = os.path.join(root, filename)
    dirpath = os.path.dirname(path)
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath)
        os.chmod(dirpath, 0o755)

    if symlink_to:
        # Если картинка уже была, то делаем симлинк
        symlink_to_abs = os.path.join(root, symlink_to)
        assert symlink_to_abs != path
        actual_link_to = os.path.relpath(symlink_to_abs, os.path.dirname(path))
        os.symlink(actual_link_to, path)
        state.last_symlinks.append(filename)

    else:
        # Если не было — создаём и запоминаем новый файл
        with open(path, "wb") as fp:
            fp.write(data)
        os.chmod(path, 0o644)
        state.last_image = filename
        state.last_rgb_sha256sum = rgb_hash
        # Старый список симлинков чистим, так как удалять дубликаты
        # с файловой системы после появления новой картинки больше не надо
        state.last_symlinks.clear()

    assert state.last_image
    assert state.last_rgb_sha256sum
    assert file_hash

    # Пилим симлинк на последнюю доступную версию
    if last_filename is not None:
        last_path = os.path.join(root, last_filename)
        if os.path.islink(last_path):
            os.unlink(last_path)
        elif os.path.exists(last_path):
            os.remove(last_path)
        actual_last_link_to = os.path.relpath(path, os.path.dirname(last_path))
        os.symlink(actual_last_link_to, last_path)

    # Пилим json-файл про последнюю доступную версию (для удобства всяких аяксов)
    if json_filename is not None:
        json_path = os.path.join(root, json_filename)
        with open(json_path, "w", encoding="utf-8") as fp1:
            json.dump({
                "last": filename,
                "last_real": state.last_image,
                "tm": tm.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tm_local": tm_local.strftime("%Y-%m-%d %H:%M:%S"),
                "sha256sum": file_hash,
                "rgb_sha256sum": rgb_hash,
            }, fp1, ensure_ascii=False, sort_keys=True, indent=2)
        os.chmod(json_path, 0o644)

    if symlink_to is not None:
        log("symlink to {} ok ({}/{})".format(
            os.path.split(symlink_to)[-1], file_hash[:6], state.last_rgb_sha256sum[:6]
        ), tm=False)
    else:
        log("ok ({}/{})".format(
            file_hash[:6], state.last_rgb_sha256sum[:6]
        ), tm=False)


def clear_old_symlinks(
    root: str,
    max_symlinks_count: int,
    delete_empty_directories: bool = True,
) -> int:
    if max_symlinks_count < 1 or len(state.last_symlinks) <= max_symlinks_count:
        return 0

    # Сохраняем немного симлинков в начале
    keep_left = max_symlinks_count // 2
    # И в конце
    keep_right = max_symlinks_count // 2 + (max_symlinks_count % 2)
    assert keep_left + keep_right == max_symlinks_count

    # Это сохраняем
    new_last_symlinks: List[str] = state.last_symlinks[:keep_left] + state.last_symlinks[-keep_right:]
    # А это удаляем
    rm_symlinks: List[str] = state.last_symlinks[keep_left:-keep_right]
    # Проверяем, что не облажались в срезах
    assert len(new_last_symlinks) + len(rm_symlinks) == len(state.last_symlinks)

    # Удаляем (если не удаляется, то и фиг с ним)
    for link_path in rm_symlinks:
        link_abspath = os.path.join(root, link_path)
        if os.path.islink(link_abspath):
            try:
                os.unlink(link_abspath)
            except Exception:
                pass

        # Если родительский каталог пустой, то давайте его тоже удалим
        if delete_empty_directories:
            link_absdir = os.path.dirname(link_abspath)
            try:
                if not os.listdir(link_absdir):
                    os.rmdir(link_absdir)
            except Exception:
                pass

    # Выжившие симлинки запоминаем
    state.last_symlinks = new_last_symlinks
    return len(rm_symlinks)


def log(msg: str, tm: bool = True, end: str = "\n") -> str:
    s: str
    if tm:
        s = "[{}] {}{}".format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            msg,
            end,
        )
    else:
        s = "{}{}".format(msg, end)

    sys.stdout.write(s)
    sys.stdout.flush()
    if log_fp is not None:
        log_fp.write(s)
        log_fp.flush()
    return s


def get_argparser_args() -> Dict[str, Any]:
    return {
        "description": "Saves VK Pixel Battle status",
    }


def configure_argparse(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--url", help="image URL (default: {})".format(default_url), default=default_url)
    parser.add_argument("--use-symlinks", default=False, action="store_true", help="Use symlinks to deduplicate files")
    parser.add_argument("-S", "--maxsize", type=float, default=5.0, help="max image size in MiB (default: 5.0)")
    parser.add_argument("-i", "--interval", type=int, default=30, help="interval between grabs in seconds (default: 30)")
    parser.add_argument("-l", "--log", default=None, help="copy stdout to this file")
    parser.add_argument("-F", "--saveopts", help="save options for PIL.Image.save (JSON, default: auto)")
    parser.add_argument("directory", metavar="DIRECTORY", help="output directory")


def main(args: argparse.Namespace) -> int:
    global state, log_fp

    saveopts: Optional[Dict[str, Any]] = None
    if args.saveopts is not None:
        saveopts = json.loads(args.saveopts)

    if saveopts is not None and not isinstance(saveopts, dict):
        raise ValueError

    interval = int(args.interval)
    if interval < 1:
        interval = 1
    maxsize = int(args.maxsize * 1024.0 * 1024.0)
    use_symlinks = bool(args.use_symlinks)
    url = args.url

    # Если будут сплошные симлинки много часов подряд, то избытки из середины
    # списка станут удаляться
    max_symlinks_count = 1440

    if args.log:
        log_fp = open(args.log, "a", encoding="utf-8", newline="")

    log("pixel_battle grabber started (interval: {}s, url: {})".format(
        interval, url
    ))

    try:
        # Создаём каталог под картинки
        root = os.path.abspath(args.directory)
        if not os.path.isdir(root):
            os.mkdir(root)

        # Загружаем состояние из файла если есть
        state_path = os.path.join(root, "state.json")
        if os.path.isfile(state_path):
            with open(state_path, "r", encoding="utf-8-sig") as fp:
                state = PixelBattleState(**dict(json.load(fp)))
            state.validate(root)

        # Ждём момента, когда можно начать качать картинку
        log("Sleeping {:.1f}s before first grab".format(
                utils.get_sleep_time(interval)
            ))
        try:
            time.sleep(utils.get_sleep_time(interval) + 0.05)
        except (KeyboardInterrupt, SystemExit):
            log("pixel_grabber finished")
            return 0

        # И качаем в вечном цикле
        while True:
            log("", tm=True, end="")
            try:
                grab(
                    url,
                    root,
                    maxsize,
                    use_symlinks=use_symlinks,
                    saveopts=saveopts,
                )
                clear_old_symlinks(root, max_symlinks_count)
                state.save(state_path)
            except (KeyboardInterrupt, SystemExit):
                log("Interrupted!", tm=False)
                break
            except Exception as exc:
                log("Failed! {}".format(exc), tm=False)
                traceback.print_exc()

            try:
                time.sleep(utils.get_sleep_time(interval) + 0.05)
            except (KeyboardInterrupt, SystemExit):
                break

        log("pixel_grabber finished")

    finally:
        if log_fp is not None:
            log_fp.close()
            log_fp = None

    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(**get_argparser_args())
    configure_argparse(p)
    sys.exit(main(p.parse_args()))
