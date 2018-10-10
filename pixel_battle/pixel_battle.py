#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pixel_battle grabber
# https://github.com/andreymal/stuff/tree/master/pixel_battle/
# copyright © 2018 andreymal
# License: MIT

import os
import sys
import json
import time
import argparse
import traceback
from io import BytesIO
from hashlib import sha256
from datetime import datetime
from urllib.request import Request, urlopen

from PIL import Image


default_url = 'http://pixel.vkforms.ru/data/1.bmp'
user_agent = 'Mozilla/5.0; pixel_battle/0.2 (grabber; https://home.andreymal.org/files/pixel_battle/; contact https://vk.com/andreymal if there are problems)'


expected_palette_old = [  # палитра первой пиксельной войны (10.10.2017)
    (24, 147, 225),
    (34, 34, 34),
    (67, 67, 67),
    (72, 141, 207),
    (75, 179, 75),
    (92, 191, 13),
    (112, 182, 247),
    (148, 224, 68),
    (153, 153, 153),    # 02 gray
    (163, 42, 185),     # 01
    (197, 210, 224),
    (205, 62, 231),
    (219, 39, 53),      #    red
    (250, 251, 252),    # 00 white
    (253, 203, 93),
    (255, 51, 71),
    (255, 114, 125),
    (255, 160, 0),
    (255, 167, 95),
]

expected_palette = [  # палитра второй пиксельной войны, но Pillow её не осилил
    (0, 0, 0),
    (24, 147, 225),
    (30, 30, 30),
    (31, 31, 31),
    (32, 32, 32),
    (43, 43, 43),
    (51, 51, 51),
    (68, 68, 68),
    (72, 141, 207),
    (75, 179, 75),
    (92, 191, 13),
    (106, 106, 106),
    (112, 182, 247),
    (147, 147, 147),
    (148, 224, 68),
    (153, 153, 153),
    (163, 42, 185),
    (187, 187, 187),
    (197, 210, 224),
    (205, 62, 231),
    (219, 39, 53),
    (239, 31, 31),
    (241, 53, 53),
    (241, 241, 241),
    (242, 74, 74),
    (248, 153, 153),
    (253, 203, 93),
    (254, 1, 0),
    (255, 114, 125),
    (255, 160, 0),
    (255, 167, 95),
    (255, 255, 255),
]


def get_sleep_time(interval=30):
    assert int(interval) == interval
    tm = time.time()
    tm_to = (int(tm) // interval + 1) * interval
    return tm_to - tm


def optimize_with_palette(im):
    '''Конвертирует полноцветную RGB картинку в картинку с фиксированной
    палитрой. Так она занимает меньше места.
    '''

    # Достаём все цвета картинки и проверяем, что они соответствуют ожидаемым
    palette = sorted(x[1] for x in im.getcolors())
    if palette != expected_palette:
        print('WARN: unexpected palette', end=' ')
        return im.copy()

    # Вот таким костылём создаём палитру для Pillow
    pal_im = Image.new('P', (256, 1))
    raw_pal = sum([list(x) for x in palette], [])
    while len(raw_pal) < 256 * 3:
        raw_pal.append(255)
    pal_im.putpalette(raw_pal)

    # Конвертируем
    small_im = im.im.convert('P', False, pal_im.im)
    small_im = im._new(small_im)

    # Проверяем, что картинка в процессе не попортилась
    # (l1 и l2 — списки RGB-кортежей, по кортежу на пиксель)
    l1 = list(small_im.convert('RGB').getdata())
    l2 = list(im.getdata())

    if len(l1) != im.size[0] * im.size[1] or l1 != l2:
        print('WARN: broken optimized image', end=' ')
        # FIXME: на Цое почему-то всегда брокен
        #im.save('/home/andreymal/stuff/pixel_battle/img/wtf_orig.png')
        #small_im.save('/home/andreymal/stuff/pixel_battle/img/wtf_compr.png')
        return im.copy()

    return small_im


def grab_to(url, dirname, filename=None, symlink_filename='last.png', json_filename='last.json', maxsize=5 * 1024 * 1024):
    # Генерируем имя сохраняемой картинки
    tm = datetime.utcnow()  # UTC
    if not filename:
        filename = time.strftime('%Y-%m-%d_%H/%Y-%m-%d_%H-%M-%S.png')  # local timezone (Europe/Moscow?)

    # Определяемся с форматом сохраняемой картинки
    ext = os.path.splitext(filename)[-1].lower().strip('.')
    if ext == 'gif':
        saveopts = {'format': 'GIF'}
    elif ext == 'png':
        saveopts = {'format': 'PNG', 'optimize': True}
    elif ext in ('jpeg', 'jpg', 'jpe'):
        saveopts = {'format': 'JPEG', 'quality': 100}
    else:
        saveopts = {'format': 'BMP'}

    # Готовим HTTP-запрос
    r = Request(url)
    r.add_header('Connection', 'close')
    r.add_header('User-Agent', user_agent)

    print('grab...', end=' ')
    sys.stdout.flush()

    # Пытаемся скачать в три попытки, а то иногда бывает ошибка 502
    tries = 3
    for trynum in range(tries):
        try:
            data = urlopen(r, timeout=10).read(maxsize + 1)
        except Exception as exc:
            print(exc, end=' ')
            sys.stdout.flush()
            if trynum >= tries - 1:
                print('fail!')
                return
        else:
            break
        time.sleep(1.5)

    if len(data) > maxsize:
        print('(image size is too big, it will be truncated!)', end=' ', flush=True)
        data = data[:maxsize]

    print('save...', end=' ')
    sys.stdout.flush()

    # Если формат не BMP (по умолчанию PNG), то конвертируем картинку в него
    if saveopts['format'] == 'PNG':
        # PNG пытаемся оптимизировать, используя фиксированную палитру
        # (для 2018 отключено из-за слишком странной палитры)
        with Image.open(BytesIO(data)) as im:
            newim = im.copy()  # optimize_with_palette(im)
            data = BytesIO()
            newim.save(data, **saveopts)
            del newim
            data = data.getvalue()

    elif saveopts['format'] != 'BMP':
        with Image.open(BytesIO(data)) as im:
            data = BytesIO()
            im.save(data, **saveopts)
            data = data.getvalue()

    # Сохраняем картинку
    path = os.path.join(dirname, filename)
    dirpath = os.path.dirname(path)
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath)
        os.chmod(dirpath, 0o755)
    with open(path, 'wb') as fp:
        fp.write(data)
    os.chmod(path, 0o644)

    # Пилим симлинк на последнюю доступную версию
    last_path = os.path.join(dirname, symlink_filename)
    if os.path.islink(last_path):
        os.unlink(last_path)
    elif os.path.exists(last_path):
        os.remove(last_path)
    os.symlink(os.path.join('.', filename), last_path)

    # Пилим ссылку на последнюю доступную версию (для удобства всяких аяксов)
    json_path = os.path.join(dirname, json_filename)
    with open(json_path, 'w', encoding='utf-8') as fp:
        json.dump({
            'last': filename,
            'tm': tm.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'sha256sum': sha256(data).hexdigest(),
        }, fp, sort_keys=True)
    os.chmod(json_path, 0o644)

    print('ok!')


def main():
    parser = argparse.ArgumentParser(description='Saves VK Pixel Battle status')
    parser.add_argument('--url', help='image URL (default: {})'.format(default_url), default=default_url)
    parser.add_argument('-S', '--maxsize', type=float, default=5.0, help='max image size in MiB (default: 5.0)')
    parser.add_argument('-i', '--interval', type=float, default=30, help='interval between grabs in seconds (default: 30)')
    parser.add_argument('directory', metavar='DIRECTORY', help='output directory')

    args = parser.parse_args()

    interval = int(args.interval)

    print(
        time.strftime('[%Y-%m-%d %H:%M:%S]'),
        'pixel_battle grabber started (interval: {}s, url: {})'.format(interval, args.url),
    )

    print(
        time.strftime('[%Y-%m-%d %H:%M:%S]'),
        'Sleeping {:.1f}s before first grab'.format(
            get_sleep_time(interval=interval)
        ),
    )
    time.sleep(get_sleep_time(interval=interval) + 0.05)

    try:
        while True:
            try:
                print(time.strftime('[%Y-%m-%d %H:%M:%S]'), end=' ')
                sys.stdout.flush()
                grab_to(args.url, args.directory, maxsize=int(args.maxsize * 1024 * 1024))
            except Exception:
                print(traceback.format_exc())
            time.sleep(get_sleep_time(interval=interval) + 0.05)

    except (KeyboardInterrupt, SystemExit):
        print()

    print(time.strftime('[%Y-%m-%d %H:%M:%S]'), 'pixel_battle grabber stopped')
    return 0


if __name__ == '__main__':
    sys.exit(main())
