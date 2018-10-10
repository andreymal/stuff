#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import argparse
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


filename_re = re.compile(r'[12][0-9]{3}-[01][0-9]-[0-3][0-9]_[0-2][0-9]-[0-6][0-9]-[0-6][0-9].png')


class ImageProcessor:
    def __init__(self, font, font_size):
        self.font = ImageFont.truetype(font, font_size)
        self.line_height = sum(self.font.getmetrics())

    def process(self, srcim, dt, label=None):
        im = Image.new('RGB', (srcim.size[0], srcim.size[1] + self.line_height), (0, 0, 0))
        with srcim.convert('RGB') as cnv:
            im.paste(cnv, (0, 0))

        if label is None:
            label = dt.strftime('%Y-%m-%d %H:%M:%S MSK')

        draw = ImageDraw.Draw(im)
        draw.text((2, im.size[1] - self.line_height), label, fill=(255, 255, 255), font=self.font)

        return im


def find_images(sourcedir):
    sourcedir = os.path.abspath(sourcedir)
    prefix = os.path.join(sourcedir, '')

    filelist = []
    for subpath, _, files in os.walk(sourcedir):
        assert subpath == sourcedir or subpath.startswith(prefix)
        for f in files:
            if not filename_re.fullmatch(f):
                continue
            filelist.append(os.path.join(subpath[len(prefix):], f))

    # В именах время, так что сортируем по времени
    filelist.sort(key=lambda x: os.path.split(x)[-1])

    return filelist


def main():
    parser = argparse.ArgumentParser(description='Prepares saved VK Pixel Battle images for video')
    parser.add_argument('-c', '--concat', help='ffconcat output filename or abspath (default: concat.txt)', default='concat.txt')
    parser.add_argument('-f', '--force', default=False, action='store_true', help='recreate already existing dest files')
    parser.add_argument('--begin', help='begin from this image (relative to sourcedir)')
    parser.add_argument('--end', help='end to this image (relative to sourcedir)')
    parser.add_argument('--font', help='font (default: arial.ttf)', default='arial.ttf')
    parser.add_argument('-fs', '--fontsize', type=int, help='font size (default: 20)', default=20)
    parser.add_argument('--extra', help='JSON file with extra configuration')
    parser.add_argument('sourcedir', metavar='SOURCEDIR', help='directory with saved images')
    parser.add_argument('destdir', metavar='DESTDIR', help='destination')

    args = parser.parse_args()

    sourcedir = os.path.abspath(args.sourcedir)
    destdir = os.path.abspath(args.destdir)
    concat_path = os.path.join(destdir, args.concat)

    # Загружаем extra конфиг из json-файла
    extra = {}
    if args.extra:
        with open(args.extra, 'r', encoding='utf-8-sig') as fp:
            extra = json.load(fp)
            if not isinstance(extra, dict):
                print('Invalid extra file')
                return 1
    extra_duration = extra.get('duration') or {}
    extra_labels = extra.get('labels') or {}

    # Собираем список всех доступных картинок
    filelist = find_images(sourcedir)

    # Урезаем его, если попросили
    if args.begin:
        try:
            f = filelist.index(args.begin)
        except ValueError:
            print(args.begin, 'not found!')
            return 1
        filelist = filelist[f:]

    if args.end:
        try:
            f = filelist.index(args.end)
        except ValueError:
            print(args.end, 'not found!')
            return 1
        filelist = filelist[:f + 1]

    for x in extra.get('ignore') or []:
        if x in filelist:
            filelist.remove(x)

    if not filelist:
        print('Images not found!')
        return 1

    print('Processing {} files'.format(len(filelist)))
    print('  begin:', filelist[0])
    print('    end:', filelist[-1])

    # Инициализируем обрабатывалку
    processor = ImageProcessor(font=args.font, font_size=args.fontsize)

    if not os.path.isdir(destdir):
        os.makedirs(destdir)

    with open(concat_path, 'w', encoding='utf-8') as concat_fp:
        concat_fp.write('ffconcat version 1.0\n\n')

        for i, relsrcpath in enumerate(filelist):
            # Сборка и проверка путей
            srcpath = os.path.join(sourcedir, relsrcpath)
            relsrcpath = relsrcpath.replace(os.path.sep, '/')

            filename = os.path.split(srcpath)[1]
            print('[{}/{}]'.format(i + 1, len(filelist)), filename, end='... ', flush=True)

            assert filename.endswith('.png')
            day, tm = filename[:-4].rsplit('_', 1)
            dt = datetime.strptime(day + ' ' + tm, '%Y-%m-%d %H-%M-%S')

            skip = False

            dstdirpath = os.path.join(destdir, day + '_' + tm[:2])
            dstpath = os.path.join(dstdirpath, filename)

            # Если готовый файл существует, то делать нечего
            if os.path.exists(dstpath):
                if not args.force:
                    print('exists, skipped;', end=' ')
                    skip = True
            elif not os.path.isdir(dstdirpath):
                os.makedirs(dstdirpath)

            # Для concat файла
            reldstpath = os.path.relpath(dstpath, start=os.path.dirname(concat_path))
            reldstpath = reldstpath.replace(os.path.sep, '/')

            if not skip:
                # Обрабатываем
                with Image.open(srcpath) as srcim:
                    dstim = processor.process(srcim, dt, label=extra_labels.get(relsrcpath))

                # Сохраняем обработанное
                # (если процесс сохранения будет прерван, то недописанный
                # файл обязательно удаляем)
                try:
                    with dstim:
                        dstim.save(dstpath, format='PNG', optimize=True)
                except:
                    if os.path.isfile(dstpath):
                        print('rm broken file')
                        os.remove(dstpath)
                    raise

            # Пишем информацию в плейлист
            for _ in range(extra_duration.get(relsrcpath) or 1):
                concat_fp.write("file '{}'\n".format(reldstpath.replace("'", "\\'")))

            print('ok.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
