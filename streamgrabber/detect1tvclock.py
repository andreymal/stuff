#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shlex
import shutil
import argparse
from subprocess import Popen, PIPE, DEVNULL

from PIL import Image


ffmpeg_cmd2 = (
    " -loglevel panic "
    "-threads 1 -r {step} -i '{path}' -q:v 1 "
    "-vf \"select=not(mod(n\\,{step})),scale=640:360\" -r 1 -vcodec rawvideo -pix_fmt rgb24 -f image2pipe -"
)

clock_color_from = (69, 101, 149)
clock_color_to = (164, 189, 220)


def is_clock(framedata):
    '''Пытается угадать, есть ли на данном кадре часы Первого канала.

    :param bytes framedata: кадр в формате RGB 640x360 (691200 байт)
    :rtype: bool
    '''

    with Image.frombytes('RGB', (640, 360), framedata) as im:
        # Если картинка синяя — значит скорее всего часы
        rgb = im.resize((1, 1), Image.BILINEAR).getdata()[0]
        # DEBUG: print('rgb', rgb, end=' ')
        if not (
            rgb[0] >= clock_color_from[0] and rgb[0] <= clock_color_to[0] and
            rgb[1] >= clock_color_from[1] and rgb[1] <= clock_color_to[1] and
            rgb[2] >= clock_color_from[2] and rgb[2] <= clock_color_to[2]
        ):
            return False
        if rgb[0] - rgb[2] > 8 or rgb[1] - rgb[2] > 8:
            return False

        # Если в центре белый пиксель — значит точно часы
        centerpixel = im.getpixel((640 // 2, 360 // 2))
        # DEBUG: print('c', centerpixel, end=' ')
        if centerpixel[0] >= 249 and centerpixel[1] >= 249 and centerpixel[2] >= 249:
            return True

        # Но часы могут быть без стрелок! https://www.youtube.com/watch?v=J1Ji_NGYtOo
        # Поэтому вводим дополнительные проверки

        ok = 0

        # Цифры по краям: 12, 3, 6, 9
        for coords in [(337, 94), (514, 173), (337, 287), (122, 173)]:
            pixel = im.getpixel(coords)
            if pixel[0] >= 150 and pixel[1] >= 180 and pixel[2] >= 200:
                ok += 1

        # Считаем кадр часами, если нашлись хотя бы две белые точки на цифрах
        if ok < 2:
            return False

        # Когда снимают снег, все точки белые; проверяем более точно, что
        # картинка синяя: откровенно красных-зелёных пикселей быть не должно
        # (логотип новостей, люди и т.п.)
        small = im.resize((64, 64), Image.BILINEAR)
        for pixel in small.getdata():
            # Оказалось, есть такие тёмные облака
            # if pixel[0] < 32 and pixel[1] < 32 and pixel[2] < 32:
            #     # Чернота
            #     # DEBUG: print('blacked', pixel, end=' ')
            #     return False
            if pixel[0] - pixel[2] > 8 or pixel[1] - pixel[2] > 8:
                # Краснота-зеленота
                # DEBUG: print('notblued', pixel, end=' ')
                return False

    return True


def find_clock_frames(path, step=75, cmd='ffmpeg'):
    '''Ищет часы Первого канала в указанном видео, анализируя некоторые кадры.
    Работает как генератор, выдавая для каждого обработанного кадра кортеж
    из трёх значений:

    - номер кадра, начиная с 1 (без учёта шага, то есть без пропусков)
    - сырые RGB данные кадра (640x360x3 байт)
    - True/False: часы или нет

    :param str path: путь к видеофайлу
    :param int step: шаг, с которым будут пропускаться кадры
    :param str cmd: команда ffmpeg или путь к нему
    '''

    cmd = (cmd + ffmpeg_cmd2).format(path=esc_cmd(path), step=step)
    cmd = shlex.split(cmd)

    stream = Popen(cmd, stdout=PIPE, stderr=DEVNULL, stdin=DEVNULL)
    fsize = 640 * 360 * 3
    frameno = -1
    while True:
        framedata = stream.stdout.read(fsize)
        if len(framedata) < fsize:
            break
        frameno += 1

        yield frameno, framedata, is_clock(framedata)



def process_video(path, args):
    if args.verbose >= 2:
        print('Processing', path)

    if not os.path.isfile(path):
        raise ValueError('File {!r} not found'.format(path))

    clock_cnt = 0
    clock_tm = None

    for frameno, framedata, ok in find_clock_frames(path, args.frame_step, args.cmd):
        if ok:
            # Отладка
            # with Image.frombytes('RGB', (640, 360), framedata) as im:
            #     im.resize((64, 64), Image.BILINEAR).save('tmp/{}_{:07d}.png'.format(os.path.split(path)[1], frameno))
            if args.verbose >= 2:
                print('{} ({}): found clock {}'.format(frameno, frame2tm(frameno, args.frame_step), clock_cnt))
            clock_cnt += 1
            if clock_cnt == 1:
                clock_tm = frame2tm(frameno, args.frame_step)
            if clock_cnt >= args.threshold:
                # Часы найдены, дальше не смотрим
                break

        else:
            # Отладка
            # with Image.frombytes('RGB', (640, 360), framedata) as im:
            #     im.resize((64, 64), Image.BILINEAR).save('no/{}_{:07d}.png'.format(os.path.split(path)[1], frameno))
            if args.verbose >= 2:
                print('{} ({}): nothing'.format(frameno, frame2tm(frameno, args.frame_step)))
            clock_cnt = 0
            clock_tm = None

    if not clock_cnt:
        if args.verbose >= 1:
            print('Clock not found')
            print()
        return

    if args.verbose >= 1:
        print('Clock found!')

    apply_action(path, action=args.mode, at=clock_tm, to=args.directory, verbose=args.verbose)

    if args.verbose:
        print()


def apply_action(path, action, at, to, verbose=0):
    '''Применяет действие по помещению видеофайла с найденными часами
    в указанный каталог. Доступные действия: notice (ничего не делает), copy,
    hardlink, symlink, move.

    :param str path: путь к исходному видеофайлу
    :param str action: выполняемое действие
    :param str at: строка вида «ЧЧ:ММ», указывающая, где найдены часы
    :param str to: каталог, в который поместить видеофайл
    :param bool verbose: если больше нуля, выводить лог в консоль
    '''

    new_name, ext = os.path.splitext(os.path.split(path)[1])
    new_name = new_name + '__at_' + at.replace(':', '-') + ext
    new_path = os.path.join(to, new_name)

    if action == 'notice':
        print('"{}": found clock at {}'.format(path, at))

    elif action == 'copy':
        if verbose:
            print('Copying video to {}...'.format(new_name), end=' ')
            sys.stdout.flush()
            shutil.copy2(path, new_path)
            print('Done.')

    elif action == 'hardlink':
        if verbose:
            print('Hardlink video to {}'.format(new_name))
        os.link(path, new_path)

    elif action == 'symlink':
        if verbose:
            print('Symlink video to {}'.format(new_name))
        link_to = os.path.relpath(path, os.path.dirname(new_path))
        os.symlink(link_to, new_path)

    elif action == 'move':
        if verbose:
            print('Moving video to {}'.format(new_name))
        os.rename(path, new_path)



def frame2tm(frameno, step):
    f = frameno * step
    tm = f // 25
    m = tm // 60
    s = tm % 60
    return '{:02d}:{:02d}'.format(m, s)


def esc_cmd(s):
    # Кавычек в начале и в конце нет, использовать примерно так:
    # "'{}'".format(esc_cmd(foo))
    return s.replace("'", "'\"'\"'").replace('\n', ' ')


def main():
    parser = argparse.ArgumentParser(description='Copies/moves video files with 1tv clock to target directory')
    parser.add_argument('-d', '--directory', help='target directory', required=True)
    parser.add_argument('-m', '--mode', default='copy', choices=('notice', 'copy', 'hardlink', 'symlink', 'move'), help='what to do with found video (copy, hardlink, symlink, move; default: copy)')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='-v: print results to stdout; -vv: print debug output')
    parser.add_argument('-f', '--frame-step', default=75, type=int, help='step between analyzed frames (default: 75)')
    parser.add_argument('-t', '--threshold', default=2, type=int, help='minimum frames count to detect clock (default: 2)')
    parser.add_argument('-c', '--cmd', default='ffmpeg', help='ffmpeg command and input arguments')

    parser.add_argument(
        'videos',
        metavar='VIDEO',
        nargs='+',
        help='path to video files (must be 25fps)',
    )

    args = parser.parse_args()

    for path in args.videos:
        process_video(path, args)

    return 0

if __name__ == '__main__':
    sys.exit(main())
