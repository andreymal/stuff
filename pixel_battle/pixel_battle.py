#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pixel_battle grabber
# copyright © 2017 andreymal
# License: MIT

import os
import sys
import json
import time
import traceback
from io import BytesIO
from hashlib import sha256
from datetime import datetime
from urllib.request import Request, urlopen

from PIL import Image


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


def get_sleep_time(interval=600):
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


def grab_to(dirname, filename=None, symlink_filename='last.png', json_filename='last.json'):
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
    r = Request('http://pixel.vkforms.ru/data/1.bmp')
    r.add_header('Connection', 'close')
    r.add_header('User-Agent', 'Mozilla/5.0; pixel_battle/0.1 (grabber; https://home.andreymal.org/files/pixel_battle/; contact https://vk.com/andreymal if there are problems)')

    print('grab...', end=' ')
    sys.stdout.flush()

    # Пытаемся скачать в три попытки, а то иногда бывает ошибка 502
    tries = 3
    for trynum in range(tries):
        try:
            data = urlopen(r).read()
        except Exception as exc:
            print(exc, end=' ')
            sys.stdout.flush()
            if trynum >= tries - 1:
                print('fail!')
                return
        else:
            break
        time.sleep(1.5)

    print('save...', end=' ')
    sys.stdout.flush()

    # Если формат не BMP (по умолчанию PNG), то конвертируем картинку в него
    if saveopts['format'] == 'PNG':
        # PNG пытаемся оптимизировать, используя фиксированную палитру
        with Image.open(BytesIO(data)) as im:
            newim = optimize_with_palette(im)
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
    if os.path.exists(last_path):
        os.remove(last_path)
    os.symlink(os.path.join('.', filename), last_path)

    # Пилим ссылку на последнюю доступную версию (для удобства всяких аяксов)
    json_path = os.path.join(dirname, json_filename)
    with open(json_path, 'w', encoding='utf-8') as fp:
        fp.write(json.dumps({'last': filename, 'tm': tm.strftime('%Y-%m-%dT%H:%M:%SZ'), 'sha256sum': sha256(data).hexdigest()}))
    os.chmod(json_path, 0o644)

    print('ok!')


def main():
    if len(sys.argv) != 2:
        print('Usage: {} dir-to-save'.format(sys.argv[0]))
        return 2

    dirname = os.path.abspath(sys.argv[1])
    if not os.path.isdir(dirname):
        os.mkdir(dirname)

    print('Sleeping {:.1f}s'.format(get_sleep_time()))
    time.sleep(get_sleep_time() + 0.05)

    try:
        while True:
            try:
                print(time.strftime('[%Y-%m-%d %H:%M:%S]'), end=' ')
                sys.stdout.flush()
                grab_to(dirname)
            except Exception:
                print(traceback.format_exc())
            time.sleep(get_sleep_time() + 0.05)

    except (KeyboardInterrupt, SystemExit):
        print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
