#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import shlex
import argparse
import subprocess


class GifEncoder:
    PIPEARG = '-'

    def __init__(self, src, begin=None, end=None, duration=None, ffmpeg_cmd='ffmpeg'):
        '''Класс, кодирующий гифку.

        :param str src: путь к видеофайлу, который будем кодировать
        :param str begin: момент видео, с которого будет начинаться гифка;
          формат ЧЧ:ММ:ДД:СС.мкс
        :param str end: момент видео, на котором будет заканчиваться гифка;
          формат ЧЧ:ММ:ДД:СС.мкс (нельзя ставить вместе с duration)
        :param str duration: итоговая длительность гифки (начиная с момента,
          указанного в begin); формат ЧЧ:ММ:ДД:СС.мкс (нельзя ставить вместе
          с end)
        :param str ffmpeg_cmd: команда ffmpeg или путь к исполняемому файлу
        '''

        self.ffmpeg_cmd = shlex.split(ffmpeg_cmd)
        if '-loglevel' not in self.ffmpeg_cmd and '-v' not in self.ffmpeg_cmd:
            self.ffmpeg_cmd.extend(['-loglevel', 'warning'])

        self.input_args = []
        if begin:
            self.input_args += ['-ss', begin]
        if end and duration:
            raise ValueError('Please set only end or duration')

        self.duration_args = []
        if duration:
            self.input_args += ['-t', duration]
        elif end:
            self.duration_args = ['-copyts', '-to', end]

        self.input_args += ['-i', src]

        self.begin = begin
        self.end = end
        self.duration = duration

        self._width = -1
        self._height = -1
        self._fps = -1
        self.filters = []
        self.update_filters()

        self.palette = None

    def update_filters(self, width=None, height=None, fps=None, custom_before=None, custom_after=None):
        '''Обновляет фильтры, применяемые к входному видеофайлу.

        :param int width: ширина (-1 — авто)
        :param int height: высота (-1 — авто)
        :param int fps: частота кадров (-1 — авто)
        :param custom_before: строка или список с произвольными фильтрами
          (добавляется перед стандартными фильтрами)
        :param custom_after: строка или список с произвольными фильтрами
          (добавляется после стандартных фильтров)
        '''

        custom_before = [custom_before] if custom_before and isinstance(custom_before, str) else custom_before
        custom_after = [custom_after] if custom_after and isinstance(custom_after, str) else custom_after

        if width is not None:
            width = max(-1, width)
            self._width = width

        if height is not None:
            height = max(-1, height)
            self._height = height

        if fps is not None:
            fps = max(-1, fps)
            self._fps = fps

        self._filters = []
        if custom_before:
            self._filters.extend(custom_before)
        if self._fps > 0:
            self.filters.append('fps={}'.format(self._fps))
        self.filters.append('scale={}:{}:flags=lanczos'.format(self._width, self._height))
        if custom_after:
            self.filters.extend(custom_after)

    def build_palette(
        self, input_path=None, output_path=None, override=False,
        max_colors=255, stats_mode='full'
    ):
        '''Генерирует палитру по содержимому входного видео. Возвращает кортеж
        с двумя значениями:

        - первый — False/True: внутренняя или внешняя палитра используется;
        - второй — если внутренняя, то палитра в формате RGBA размером 16*16*4
          байт; если внешний, то путь к картинке с палитрой.

        :param str input_path: использовать внешнюю палитру; путь к картинке
          16x16. Если указан, остальные параметры игрорируются
        :param str output_path: путь, куда сохранить свежесозданную палитру
        :param bool override: если True, перезаписать свежесозданную палитру
          по указанному пути, даже если файл по этому пути уже существует
        :param int max_colors: максимальное число цветов в палитре
        :param str stats_mode: см. справку по фильтру palettegen в ffmpeg
        '''

        if input_path:
            self.palette = (True, input_path)
            return self.palette

        if max_colors < 255:
            pgen = 'palettegen=max_colors={}:'.format(max_colors)
        else:
            pgen = 'palettegen='
        pgen += 'stats_mode={}:reserve_transparent=0'.format(stats_mode)

        palette_cmd = self.ffmpeg_cmd + self.input_args + self.duration_args
        palette_cmd += ['-vf', ','.join(self.filters + [pgen])]

        if output_path:
            if override:
                palette_cmd.append('-y')
            palette_cmd.append(output_path)
        else:
            palette_cmd.extend(['-pix_fmt', 'rgb32', '-f', 'rawvideo', self.PIPEARG])

        palette = subprocess.check_output(palette_cmd, stdin=subprocess.DEVNULL)
        if output_path:
            self.palette = (True, output_path)
            return self.palette

        if len(palette) != 1024:
            raise RuntimeError('ffmpeg returned invalid palette')

        self.palette = (False, palette)
        return self.palette

    def build_gif(self, path, override=False, dither='sierra2_4a'):
        '''Конвертирует гифку, сохраняя её по указанному пути. Если палитра
        не была создана методом ``build_palette``, то создаёт палитру
        с параметрами по умолчанию.

        :param str path: путь, куда сохранить гифку
        :param str dither: алгоритм дизеринга; см. справку по фильтру
          paletteuse в ffmpeg
        '''

        if not self.palette:
            self.build_palette()

        is_external_palette, palette_data = self.palette

        gif_cmd = self.ffmpeg_cmd + self.input_args

        if is_external_palette:
            gif_cmd += ['-i', palette_data]
        else:
            gif_cmd += ['-pix_fmt', 'rgb32', '-f', 'rawvideo', '-video_size', '16x16', '-i', self.PIPEARG]

        gif_cmd += self.duration_args

        gif_cmd += ['-lavfi', ','.join(self.filters) + ' [x]; [x][1:v] paletteuse=']

        gif_cmd[-1] += 'dither={}'.format(dither)

        if override:
            gif_cmd.append('-y')
        gif_cmd.append(path)

        ffmpeg = subprocess.Popen(gif_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
        if not is_external_palette:
            ffmpeg.stdin.write(palette_data)
        ffmpeg.stdin.close()
        if ffmpeg.wait() != 0:
            raise RuntimeError('ffmpeg exited with non-zero error code')


def main():
    parser = argparse.ArgumentParser(description='Converts video to gif using ffmpeg.')

    parser.add_argument(
        'src',
        metavar='SOURCE',
        help='path to source video file',
    )
    parser.add_argument(
        'dst',
        metavar='DESTINATION',
        help='path to destination gif file',
    )

    # input args
    parser.add_argument('-ss', '--begin', default=None, help='video begin position (e.g. 00:00:05.500 will skip first 5.5 seconds of video)')
    parser.add_argument('-to', '--end', default=None, help='video end position (e.g. --begin 00:00:05.500 --end 00:00:07.000 will create 1.5s gif)')
    parser.add_argument('-t', '--duration', default=None, help='gif duration (e.g. 00:00:01.500) (cannot be used with --end option)')
    parser.add_argument('-vf', '--videofilter', default=None, help='custom ffmpeg video filters (will be added after resizing filters)')

    # output args (excl. w/h/r)
    parser.add_argument('-W', '--width', type=int, default=-1, help='set image width (default: as in source video)')
    parser.add_argument('-H', '--height', type=int, default=-1, help='set image height (default: as in source video)')
    parser.add_argument('-r', '--fps', type=int, default=0, help='set frames count per second (default: as in source video)')
    parser.add_argument('-m', '--colors', type=int, default=255, help='colors count for gif palette (2-255; default 255)')
    parser.add_argument('-s', '--stats-mode', default='full', choices=('full', 'diff'), help='palettegen statistics mode: full (default) or diff; see ffmpeg docs')
    parser.add_argument('-P', '--save-palette', help='save autogenerated palette to specified path')
    parser.add_argument('-p', '--palette', help='use custom palette (path to 16x16 image)')
    parser.add_argument('-d', '--dither', default='sierra2_4a', help='dithering mode for paletteuse filter; see ffmpeg docs')
    parser.add_argument('-y', '--override', default=False, action='store_true', help='force override destination gif if it already exists')

    # misc args
    parser.add_argument('-c', '--ffmpeg-cmd', help='path to ffmpeg program (default: ffmpeg)', default='ffmpeg')

    args = parser.parse_args()

    if args.end and args.duration:
        print('Please set only --end or --duration argument', file=sys.stderr)
        return 1

    encoder = GifEncoder(args.src, ffmpeg_cmd=args.ffmpeg_cmd, begin=args.begin, end=args.end, duration=args.duration)
    encoder.update_filters(
        width=args.width,
        height=args.height,
        fps=args.fps,
        custom_before=None,
        custom_after=args.videofilter,
    )

    # Шаг первый: создание палитры
    if not args.palette:
        print('Generate palette...', file=sys.stderr)
        tm = time.time()
        encoder.build_palette(
            max_colors=args.colors,
            stats_mode=args.stats_mode,
            output_path=args.save_palette,
            override=args.override,
        )
        print('Done in {:.2f}s'.format(time.time() - tm))

    else:
        encoder.build_palette(input_path=args.palette)
        print('Use custom palette', file=sys.stderr)

    # Шаг второй: создание гифки
    print('Create gif...', file=sys.stderr)
    tm = time.time()
    encoder.build_gif(
        args.dst,
        override=args.override,
        dither=args.dither,
    )
    print('Done in {:.2f}s'.format(time.time() - tm))
    size_k = os.stat(args.dst).st_size / 1024.0
    if size_k >= 1536:
        print('File size: {:.2f} MiB'.format(size_k / 1024.0))
    else:
        print('File size: {:.2f} KiB'.format(size_k))

    return 0


if __name__ == '__main__':
    sys.exit(main())
