#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


palette = [
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

    # for text:
    (0, 0, 0),
    (115, 115, 115),
    (192, 192, 192),
    (255, 255, 255),
]


custom_dates = {
    "2017-10-10_00-00-00_tk00005.png": datetime(2017, 10, 10, 16, 0, 0),
    "2017-10-10_00-00-00_tk00006.png": datetime(2017, 10, 10, 16, 10, 0),
    "2017-10-10_00-00-00_tk00007.png": datetime(2017, 10, 10, 16, 20, 0),
    "2017-10-10_00-00-00_tk00008.png": datetime(2017, 10, 10, 16, 30, 0),
    "2017-10-10_00-00-00_tk00009.png": datetime(2017, 10, 10, 16, 40, 0),
    "2017-10-10_00-00-00_tk00010.png": datetime(2017, 10, 10, 16, 50, 0),
    "2017-10-10_00-00-00_tk00011.png": datetime(2017, 10, 10, 17, 0, 0),
    "2017-10-10_00-00-00_tk00012.png": datetime(2017, 10, 10, 17, 10, 0),
    "2017-10-10_00-00-00_tk00013.png": datetime(2017, 10, 10, 17, 20, 0),
    "2017-10-10_00-00-00_tk00014.png": datetime(2017, 10, 10, 17, 30, 0),
    "2017-10-10_00-00-00_tk00015.png": datetime(2017, 10, 10, 17, 40, 0),
    "2017-10-10_00-00-00_tk00016.png": datetime(2017, 10, 10, 17, 50, 0),
    "2017-10-10_00-00-00_tk00017.png": datetime(2017, 10, 10, 18, 0, 0),
    "2017-10-10_00-00-00_tk00018.png": datetime(2017, 10, 10, 18, 10, 0),
    "2017-10-10_00-00-00_tk00019.png": datetime(2017, 10, 10, 18, 20, 0),
    "2017-10-10_00-00-00_tk00020.png": datetime(2017, 10, 10, 18, 30, 0),
    "2017-10-10_00-00-00_tk00021.png": datetime(2017, 10, 10, 18, 40, 0),
    "2017-10-10_00-00-00_tk00022.png": datetime(2017, 10, 10, 18, 50, 0),
    "2017-10-10_00-00-00_tk00023.png": datetime(2017, 10, 10, 19, 0, 0),
    "2017-10-10_00-00-00_tk00024.png": datetime(2017, 10, 10, 19, 10, 0),
    "2017-10-10_00-00-00_tk00025.png": datetime(2017, 10, 10, 19, 20, 0),
    "2017-10-10_00-00-00_tk00026.png": datetime(2017, 10, 10, 19, 30, 0),
    "2017-10-10_00-00-00_tk00027.png": datetime(2017, 10, 10, 19, 40, 0),
    "2017-10-10_00-00-00_tk00028.png": datetime(2017, 10, 10, 19, 50, 0),
    "2017-10-10_00-00-00_tk00029.png": datetime(2017, 10, 10, 20, 0, 0),
    "2017-10-10_00-00-00_tk00030.png": datetime(2017, 10, 10, 20, 10, 0),
    "2017-10-10_00-00-00_tk00031.png": datetime(2017, 10, 10, 20, 20, 0),
    "2017-10-10_00-00-00_tk00032.png": datetime(2017, 10, 10, 20, 30, 0),
    "2017-10-10_00-00-00_tk00033.png": datetime(2017, 10, 10, 20, 40, 0),
    "2017-10-10_00-00-00_tk00034.png": datetime(2017, 10, 10, 20, 50, 0),
    "2017-10-10_00-00-00_tk00035.png": datetime(2017, 10, 10, 21, 0, 0),
    "2017-10-10_00-00-00_tk00036.png": datetime(2017, 10, 10, 21, 10, 0),
    "2017-10-10_00-00-00_tk00037.png": datetime(2017, 10, 10, 21, 20, 0),
    "2017-10-10_00-00-00_tk00038.png": datetime(2017, 10, 10, 21, 30, 0),
    "2017-10-10_00-00-00_tk00039.png": datetime(2017, 10, 10, 21, 40, 0),
    "2017-10-10_00-00-00_tk00040.png": datetime(2017, 10, 10, 21, 50, 0),
    "2017-10-10_00-00-00_tk00041.png": datetime(2017, 10, 10, 22, 0, 0),
    "2017-10-10_00-00-00_tk00042.png": datetime(2017, 10, 10, 22, 10, 0),
    "2017-10-10_00-00-00_tk00043.png": datetime(2017, 10, 10, 22, 20, 0),
    "2017-10-10_00-00-00_tk00044.png": datetime(2017, 10, 10, 22, 30, 0),
    "2017-10-10_00-00-00_tk00045.png": datetime(2017, 10, 10, 22, 40, 0),
    "2017-10-10_00-00-00_tk00046.png": datetime(2017, 10, 10, 22, 50, 0),
    "2017-10-10_00-00-00_tk00047.png": datetime(2017, 10, 10, 23, 0, 0),
    "2017-10-10_00-00-00_tk00048.png": datetime(2017, 10, 10, 23, 10, 0),
}


custom_labels = {
    "2017-10-10_00-00-00_tk00005.png": "2017-10-10 ≈16:00 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00006.png": "2017-10-10 ≈16:10 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00007.png": "2017-10-10 ≈16:20 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00008.png": "2017-10-10 ≈16:30 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00009.png": "2017-10-10 ≈16:40 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00010.png": "2017-10-10 ≈16:50 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00011.png": "2017-10-10 ≈17:00 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00012.png": "2017-10-10 ≈17:10 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00013.png": "2017-10-10 ≈17:20 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00014.png": "2017-10-10 ≈17:30 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00015.png": "2017-10-10 ≈17:40 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00016.png": "2017-10-10 ≈17:50 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00017.png": "2017-10-10 ≈18:00 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00018.png": "2017-10-10 ≈18:10 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00019.png": "2017-10-10 ≈18:20 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00020.png": "2017-10-10 ≈18:30 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00021.png": "2017-10-10 ≈18:40 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00022.png": "2017-10-10 ≈18:50 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00023.png": "2017-10-10 ≈19:00 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00024.png": "2017-10-10 ≈19:10 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00025.png": "2017-10-10 ≈19:20 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00026.png": "2017-10-10 ≈19:30 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00027.png": "2017-10-10 ≈19:40 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00028.png": "2017-10-10 ≈19:50 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00029.png": "2017-10-10 ≈20:00 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00030.png": "2017-10-10 ≈20:10 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00031.png": "2017-10-10 ≈20:20 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00032.png": "2017-10-10 ≈20:30 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00033.png": "2017-10-10 ≈20:40 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00034.png": "2017-10-10 ≈20:50 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00035.png": "2017-10-10 ≈21:00 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00036.png": "2017-10-10 ≈21:10 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00037.png": "2017-10-10 ≈21:20 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00038.png": "2017-10-10 ≈21:30 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00039.png": "2017-10-10 ≈21:40 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00040.png": "2017-10-10 ≈21:50 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00041.png": "2017-10-10 ≈22:00 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00042.png": "2017-10-10 ≈22:10 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00043.png": "2017-10-10 ≈22:20 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00044.png": "2017-10-10 ≈22:30 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00045.png": "2017-10-10 ≈22:40 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00046.png": "2017-10-10 ≈22:50 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00047.png": "2017-10-10 ≈23:00 MSK (from www.pixel-history.tk)",
    "2017-10-10_00-00-00_tk00048.png": "2017-10-10 ≈23:10 MSK (from www.pixel-history.tk)",
}


def optimize_with_palette(im):
    # palette = sorted(x[1] for x in im.getcolors())

    # Вот таким костылём создаём палитру для Pillow
    pal_im = Image.new('P', (256, 1))
    raw_pal = sum([list(x) for x in palette], [])
    while len(raw_pal) < 256 * 3:
        raw_pal.append(255)
    pal_im.putpalette(raw_pal)

    # Конвертируем
    small_im = im.im.convert('P', False, pal_im.im)
    small_im = im._new(small_im)

    #l1 = list(small_im.convert('RGB').getdata())
    #l2 = list(im.getdata())

    #if len(l1) != im.size[0] * im.size[1] or l1 != l2:
    #    print('WARN: broken optimized image', end=' ')
    #    return im.copy()

    return small_im


fromdir = './img'
todir = './my/src'
datetable_path = './my/datetable.txt'  # формат создаваемого файла: номера строк — номер кадра (счёт с нуля), содержимое — дата кадра YYYY-MM-DDTHH:MM:SS+03:00

font = ImageFont.truetype('arial.ttf', 20)
line_height = sum(font.getmetrics())


# Собираем список кадров для обработки
filelist = []
for subpath, _, files in os.walk(fromdir):
    for f in files:
        if not f.endswith('.png') or not f.startswith('201'):
            continue
        filelist.append(os.path.abspath(
            os.path.join(fromdir, subpath, f)
        ))

# В именах время, так что сортируем по времени
filelist.sort(key=lambda x: os.path.split(x)[-1])


with open(datetable_path, 'w', encoding='utf-8') as fp:
    # i - номер текущего кадра
    i = 0
    for path in filelist:
        f = os.path.split(path)[-1]
        if not f.endswith('.png') or not f.startswith('201'):
            continue
        outpath = os.path.join(todir, '{:09d}.png'.format(i))
        fnum = i
        i += 1

        if f in custom_dates:
            date = custom_dates[f]
        else:
            date = datetime.strptime(f, '%Y-%m-%d_%H-%M-%S.png')

        fp.write('{:09d} {}\n'.format(fnum, date.strftime('%Y-%m-%dT%H:%M:%S+03:00')))

        if os.path.isfile(outpath):
            # print(f, 'skip')
            continue

        if f in custom_labels:
            label = custom_labels[f]
        else:
            label = date.strftime('%Y-%m-%d %H:%M:%S MSK')

        with Image.open(path) as im_orig:
            im = Image.new('RGB', (im_orig.size[0], im_orig.size[1] + line_height), (0, 0, 0))
            im.paste(im_orig.convert('RGB'), (0, 0))

        draw = ImageDraw.Draw(im)
        draw.text((2, im.size[1] - line_height), label, fill=(255, 255, 255), font=font)

        im = optimize_with_palette(im)
        try:
            im.save(outpath, format='PNG', optimize=True)
        except:
            if os.path.isfile(outpath):
                print('rm broken file')
                os.remove(outpath)
            raise
        print(fnum, f, '-', label)
