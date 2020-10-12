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
from typing import Any, Optional, Tuple, List, Dict, TextIO
import dataclasses
from dataclasses import dataclass

from PIL import Image

from . import utils


default_url = "https://pixel-dev.w84.vkforms.ru/api/data"
default_top_url = "https://pixel-dev.w84.vkforms.ru/api/top"
user_agent = "Mozilla/5.0; pixel_battle/0.3.4 (grabber; https://github.com/andreymal/stuff/tree/master/pixel_battle)"
log_fp: Optional[TextIO] = None


@dataclass
class PixelBattleState:
    last_image: Optional[str] = None  # Никогда не бывает симлинком, а путь всегда относительный
    last_rgb_sha256sum: Optional[str] = None
    # Список относительных путей к симлинкам
    last_symlinks: List[str] = dataclasses.field(default_factory=list)
    # Палитра для преобразвания букв в цвета
    palette: Dict[str, bytes] = dataclasses.field(default_factory=lambda: {"_": b"\xff\x00\xff"})
    # Размеры читаемой картинки
    width: int = 1590
    height: int = 400

    def clear_last_image(self) -> None:
        self.last_image = None
        self.last_rgb_sha256sum = None
        self.last_symlinks.clear()

    def validate_last_image(self, root: str) -> None:
        if not self.last_image:
            self.clear_last_image()
            return

        last_image = os.path.join(root, self.last_image)
        if not os.path.isfile(last_image) or os.path.islink(last_image):
            self.clear_last_image()
            log("Last image {!r} not found, ignored".format(last_image))
            return

        try:
            h = utils.rgb_sha256sum(last_image)
        except Exception:
            self.clear_last_image()
            log("Last image {!r} cannot be read, ignored".format(last_image))
            return

        if h != self.last_rgb_sha256sum:
            self.clear_last_image()
            log("Last image {!r} was changed, ignored".format(last_image))

    def validate(self, root: str) -> None:
        self.validate_last_image(root)

    def save(self, path: str) -> None:
        data = dataclasses.asdict(self)
        data.pop("palette")
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(
                data,
                fp,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )


global_state = PixelBattleState()


def download(
    url: str,
    maxsize: int = 5 * 1024 * 1024,
    tries: int = 2,
    tries_interval: float = 0.5,
    timeout: int = 4,
    headers: Optional[Dict[str, Optional[str]]] = None,
    expected_minsize: Optional[int] = None,
) -> Optional[bytes]:
    # Готовим HTTP-запрос
    r = Request(url)
    r.add_header("User-Agent", user_agent)

    if headers:
        for k, v in headers.items():
            if v:
                r.add_header(k, v)

    # Пытаемся скачать в несколько попыток, а то иногда бывает ошибка 502
    data = b""
    for trynum in range(tries):
        try:
            data = urlopen(r, timeout=timeout).read(maxsize + 1)
        except Exception as exc:
            log(str(exc), tm=False, end="; ")
            if trynum >= tries - 1:
                return None
        else:
            if expected_minsize is None or len(data) >= expected_minsize:
                # Сервер иногда отдаёт обрезанный ответ, поэтому вот базовая проверка, что он не обрезан
                break
            else:
                log("truncated", tm=False, end="; ")
        time.sleep(tries_interval)

    if len(data) > maxsize:
        log("(image size is too big, it will be truncated!)", tm=False, end=" ")
        data = data[:maxsize]

    return data


def grab(
    root: str,
    url: str,
    top_url: Optional[str] = None,
    maxsize: int = 5 * 1024 * 1024,
    use_symlinks: bool = False,
    filename: Optional[str] = None,
    filename_format: str = "%Y-%m-%d_%H/%Y-%m-%d_%H-%M-%S.png",
    filename_meta: Optional[str] = None,
    filename_meta_format: str = "%Y-%m-%d_%H/%Y-%m-%d_%H-%M-%S_meta.json",
    filename_top: Optional[str] = None,
    filename_top_format: str = "%Y-%m-%d_%H/%Y-%m-%d_%H-%M-%S_top.json",
    filename_utc: bool = False,
    saveopts: Optional[Dict[str, Any]] = None,
    last_filename: Optional[str] = "last.png",
    json_filename: Optional[str] = "last.json",
    directory_mode: Optional[int] = None,
    file_mode: Optional[int] = None,
    randomize_urls: bool = True,
    state: Optional[PixelBattleState] = None,
    top_vk_sign: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    if state is None:
        state = global_state

    # Генерируем имя сохраняемых файлов
    tm = datetime.utcnow()  # UTC
    tm_local = datetime.now()  # local timezone

    # Обходим кривое кэширование на стороне сервера
    if randomize_urls:
        rnd = "{m}-{h}".format(m=tm_local.minute, h=tm_local.hour)
        url += ("&" if "?" in url else "?") + "ts=" + rnd
        if top_url:
            top_url += ("&" if "?" in top_url else "?") + "ts=" + rnd

    if not filename:
        if filename_utc:
            filename = tm.strftime(filename_format)
        else:
            filename = tm_local.strftime(filename_format)

    if not filename_meta and filename_meta_format:
        if filename_utc:
            filename_meta = tm.strftime(filename_meta_format)
        else:
            filename_meta = tm_local.strftime(filename_meta_format)

    if not filename_top and filename_top_format:
        if filename_utc:
            filename_top = tm.strftime(filename_top_format)
        else:
            filename_top = tm_local.strftime(filename_top_format)

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

    # Скачиваем пиксели (они отдаются в виде текстовых символов)
    log("[im:", tm=False, end=" ")
    orig_data_bin: Optional[bytes] = download(url, maxsize, expected_minsize=state.width * state.height)
    if orig_data_bin is None:
        log("fail]", tm=False)
        return None, None
    log("ok]", tm=False, end=" ")
    orig_data: str = orig_data_bin.decode("utf-8")

    # Запоминаем реальное время скачивания
    im_unixtime = time.time()

    # Сразу скачиваем топ
    top_data_bin: Optional[bytes] = None
    if top_url is not None:
        log("[top:", tm=False, end=" ")
        top_data_bin = download(top_url, maxsize, timeout=1, headers={"X-vk-sign": top_vk_sign})
        if top_data_bin is None:
            log("fail]", tm=False, end=" ")
        else:
            log("ok]", tm=False, end=" ")

    # Запоминаем реальное время скачивания
    top_unixtime = time.time()

    # Декодируем текстовые символы в нормальные цвета
    log("[decode:", tm=False, end=" ")
    imglen = state.width * state.height
    imgdata = orig_data[:imglen]  # Откусываем JSON-мусор (снежинки) в конце
    metadata = orig_data[imglen:].strip()
    if len(imgdata) < imglen:
        log("WARNING: truncated image!", tm=False, end=" ")
        imgdata += "_" * (imglen - len(imgdata))
    elif len(orig_data) > imglen and orig_data[imglen] != "[":
        log("WARNING: unexpected extra data")

    img_rgb = utils.decode_image(imgdata, state.palette)
    log("ok]", tm=False, end=" ")

    log("[save:", tm=False, end=" ")

    symlink_to: Optional[str] = None
    data = b""
    file_hash = ""

    with Image.frombytes("RGB", (state.width, state.height), img_rgb) as im:
        # if im.mode != "RGB":
        #     raise NotImplementedError("Unsupported image mode: {!r}".format(im.mode))

        # Считаем хэш содержимого (не bmp-файла, а именно содержимого пикселей в RGB)
        # rgb_hash = utils.rgb_sha256sum(im)
        rgb_hash = utils.sha256sum(img_rgb)
        assert rgb_hash == utils.rgb_sha256sum(im)

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
        if directory_mode is not None:
            os.chmod(dirpath, directory_mode)

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
        os.utime(path, (im_unixtime, im_unixtime))
        if file_mode is not None:
            os.chmod(path, file_mode)
        state.last_image = filename
        state.last_rgb_sha256sum = rgb_hash
        # Старый список симлинков чистим, так как удалять дубликаты
        # с файловой системы после появления новой картинки больше не надо
        state.last_symlinks.clear()

    assert state.last_image
    assert state.last_rgb_sha256sum
    assert file_hash

    # Пилим симлинк на последнюю доступную версию
    # (путём создания временного файла и перемещения, чтоб атомарно было)
    if last_filename is not None:
        last_path = os.path.join(root, last_filename)
        last_path_tmp = last_path + ".tmp"
        if os.path.exists(last_path_tmp):
            os.remove(last_path_tmp)
        actual_last_link_to = os.path.relpath(path, os.path.dirname(last_path))
        os.symlink(actual_last_link_to, last_path_tmp)
        os.rename(last_path_tmp, last_path)

    # Пилим json-файл про последнюю доступную версию (для удобства всяких аяксов)
    # (тоже атомарно)
    if json_filename is not None:
        json_path = os.path.join(root, json_filename)
        json_path_tmp = json_path + ".tmp"
        with open(json_path_tmp, "w", encoding="utf-8") as fp1:
            json.dump({
                "last": filename,
                "last_real": state.last_image,
                "tm": tm.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tm_local": tm_local.strftime("%Y-%m-%d %H:%M:%S"),
                "sha256sum": file_hash,
                "rgb_sha256sum": rgb_hash,
            }, fp1, ensure_ascii=False, sort_keys=True, indent=2)
        if file_mode is not None:
            os.chmod(json_path_tmp, file_mode)
        os.rename(json_path_tmp, json_path)

    # Заодно сохраняем мету (информацию о замороженных точках) и топ
    if filename_meta and metadata:
        try:
            metadata_decoded: List[Any] = list(json.loads(metadata))
        except Exception:
            log("(invalid meta)", tm=False, end=" ")
        else:
            with open(os.path.join(root, filename_meta), "w", encoding="utf-8") as tfp:
                tfp.write(metadata)
            os.utime(os.path.join(root, filename_meta), (im_unixtime, im_unixtime))

    if filename_top and top_data_bin:
        try:
            top_data_decoded: Dict[str, Any] = dict(json.loads(top_data_bin.decode("utf-8")))
        except Exception:
            log("(invalid top)", tm=False, end=" ")
        else:
            with open(os.path.join(root, filename_top), "wb") as fp:
                fp.write(top_data_bin)
            os.utime(os.path.join(root, filename_top), (top_unixtime, top_unixtime))

    if symlink_to is not None:
        log("ok] symlink to {} ({}/{})".format(
            os.path.split(symlink_to)[-1], file_hash[:6], state.last_rgb_sha256sum[:6]
        ), tm=False)
    else:
        log("ok] ({}/{})".format(
            file_hash[:6], state.last_rgb_sha256sum[:6]
        ), tm=False)

    return filename, symlink_to


def clear_old_symlinks(
    root: str,
    max_symlinks_count: int,
    delete_empty_directories: bool = True,
    state: Optional[PixelBattleState] = None,
) -> int:
    if state is None:
        state = global_state

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
    parser.add_argument("-p", "--palette", required=True, help="palette file (json)")
    parser.add_argument("--url", help="image data URL (default: {})".format(default_url), default=default_url)
    parser.add_argument("--top-url", help="top data URL (default: {})".format(default_top_url), default=default_top_url)
    parser.add_argument("--top-vk-sign", help="X-vk-sign header for top request", default=None)
    parser.add_argument("--use-symlinks", default=False, action="store_true", help="Use symlinks to deduplicate files")
    parser.add_argument("--max-symlinks-count", type=int, default=1440, help="maximum number of symlinks pointing to the same file (0 is infinity; default: 1440)")
    parser.add_argument("-S", "--maxsize", type=float, default=5.0, help="max image size in MiB (default: 5.0)")
    parser.add_argument("-i", "--interval", type=int, default=30, help="interval between grabs in seconds (default: 30)")
    parser.add_argument("-l", "--log", default=None, help="copy stdout to this file")
    parser.add_argument("-F", "--saveopts", help="save options for PIL.Image.save (JSON, default: auto)")
    parser.add_argument("-U", "--umask", default=None, help="set umask (022 is recommended)")
    parser.add_argument("directory", metavar="DIRECTORY", help="output directory")


def main(args: argparse.Namespace) -> int:
    global global_state, log_fp

    if args.umask:
        os.umask(int(args.umask, 8))

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
    top_url = args.top_url
    top_vk_sign = args.top_vk_sign

    # Если будут сплошные симлинки много часов подряд, то избытки из середины
    # списка станут удаляться
    max_symlinks_count = args.max_symlinks_count

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
            global_state = state
        else:
            state = global_state

        # Загружаем палитру из файла
        state.palette = utils.read_palette(args.palette)

        # Ждём момента, когда можно начать качать картинку
        log("Sleeping {:.1f}s before first grab".format(
                utils.get_sleep_time(interval)
            ))
        try:
            time.sleep(utils.get_sleep_time(interval) + 0.05)
        except (KeyboardInterrupt, SystemExit):
            log("pixel_battle grabber finished")
            return 0

        # И качаем в вечном цикле
        while True:
            log("", tm=True, end="")
            try:
                grab(
                    root,
                    url,
                    top_url,
                    maxsize,
                    use_symlinks=use_symlinks,
                    saveopts=saveopts,
                    state=state,
                    top_vk_sign=top_vk_sign,
                )
                clear_old_symlinks(root, max_symlinks_count, state=state)
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

        log("pixel_battle grabber finished")

    finally:
        if log_fp is not None:
            log_fp.close()
            log_fp = None

    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(**get_argparser_args())
    configure_argparse(p)
    sys.exit(main(p.parse_args()))
