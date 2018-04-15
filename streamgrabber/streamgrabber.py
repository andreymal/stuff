#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import shlex
import shutil
import argparse
from subprocess import Popen, DEVNULL, PIPE
from datetime import datetime
from threading import RLock

import watchdog.observers
import watchdog.events


default_input_args ='-loglevel panic'
default_output_args = '-y -c copy -map 0 -segment_time_delta 10 -reset_timestamps 1'


observer = None
outputfmt = None
max_segments = None
commands = []
working_directory = '.'

cache_lock = RLock()
cache_path = None
last_files = []


# watchdog thread


class Handler(watchdog.events.FileSystemEventHandler):
    def on_created(self, event):
        '''Этот метод вызывается при появлении нового файла в текущем
        каталоге. Имейте в виду, что watchdog пихает его в отдельный поток.
        '''

        # Проверяем, что это наш файл-сегмент
        filename = os.path.split(event.src_path)[1]
        if not filename.startswith('_sgout-'):
            return

        # Переименовываем в дату (ffmpeg успешно продолжает в него писать)
        new_filename = datetime.now().strftime(outputfmt)
        if os.path.dirname(new_filename) and not os.path.isdir(os.path.dirname(new_filename)):
            os.makedirs(os.path.dirname(new_filename))

        path = os.path.abspath(os.path.join(working_directory, new_filename))

        os.rename(
            os.path.join(working_directory, filename),
            path
        )

        log('Created', new_filename)

        # Удаляем слишком старые файлы, чтобы не занимать место
        while max_segments > 0 and len(last_files) >= max_segments:
            log('Removed old file {}'.format(last_files[0]))
            try:
                os.remove(last_files.pop(0))
            except Exception as exc:
                log('Fail: {}'.format(exc))

        # Видимо, у предыдущего сегмента запись завершена, и его можно
        # обработать
        file_to_process = None
        if last_files:
            file_to_process = last_files[-1]
        last_files.append(path)
        save_cache()

        if file_to_process:
            process_segment(file_to_process)


def process_segment(path):
    log('Processing', path)

    # Просто запускаем все команды по очереди
    for cmd in commands:
        if not os.path.isfile(path):
            log(path, 'was removed, processing is stopped')
            if path in last_files:
                last_files.remove(path)
                save_cache()
            break

        exitcode = Popen(cmd + [path], stdin=DEVNULL).wait()
        if exitcode != 0:
            log('WARNING: command exited with code {}:'.format(exitcode), cmdlist_to_str(cmd + [path]))

    log('Finished processing')


def prepare_watchdog():
    global observer

    observer = watchdog.observers.Observer()
    observer.schedule(Handler(), working_directory, recursive=False)
    observer.start()


# ffmpeg thread


def run_ffmpeg_forever(ffmpeg_cmd):
    '''Следит за работоспособностью ffmpeg и корректно его завершает.'''

    ffmpeg = None

    try:
        while True:
            ffmpeg = Popen(ffmpeg_cmd, stdin=PIPE, stdout=DEVNULL, stderr=DEVNULL)
            time.sleep(0.2)
            if ffmpeg.poll() is None:
                log('ffmpeg started')
            exitcode = ffmpeg.wait()
            ffmpeg = None
            log('ffmpeg exited with code {}, restarting'.format(exitcode))
            time.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        print('\r', end='')
        log('Stopping')

    finally:
        if ffmpeg and ffmpeg.poll() is None:
            ffmpeg.stdin.write(b'q')
            ffmpeg.stdin.flush()
            ffmpeg.wait(timeout=10)
        ffmpeg = None


def build_ffmpeg_cmd(stream, input_args=default_input_args, output_args=default_output_args, output='%Y-%m-%d_%H-%M-%S.mp4', duration=1200, fmt='mp4', ffmpeg_path='ffmpeg'):
    '''Конструирует готовую команду ffmpeg, которая будет записывать сегменты
    из стрима.

    :param str stream: адрес входного потока
    :param str input_args: ffmpeg параметры входного потока
    :param str output_args: ffmpeg параметры кодирования сегментов
    :param str output: шаблон названий сегментов; строка, которая будет
      передана в strftime с датой создания файла
    :param int duration: длительность одного сегмента в секундах
    :param str fmt: формат сегментов
    :param str ffmpeg_path: путь к ffmpeg или просто используемая команда
    '''

    ext = os.path.splitext(output)[1]

    ffmpeg_path = shutil.which(ffmpeg_path)
    if not ffmpeg_path:
        raise ValueError('ffmpeg not found')

    cmd = [ffmpeg_path]
    if input_args:
        cmd.extend(shlex.split(input_args.replace('$$', default_input_args)))

    cmd.append('-i')
    cmd.append(stream)

    if output_args:
        cmd.extend(shlex.split(output_args.replace('$$', default_output_args)))

    cmd.append('-f')
    cmd.append('segment')
    cmd.append('-segment_time')
    cmd.append(str(duration))
    cmd.append('-segment_format')
    cmd.append(fmt)
    cmd.append(os.path.join(working_directory, '_sgout-%07d' + ext))

    return cmd


# utils


def log(*args):
    print(datetime.now().strftime('[%Y-%m-%d %H:%M:%S]'), *args)


def cmdlist_to_str(cmd):
    cmd_string = []
    for x in cmd:
        if ' ' in x or '"' in x or "'" in x:
            x = "'" + x.replace("'", "'\"'\"'").replace('\n', ' ') + "'"
        cmd_string.append(x)
    return ' '.join(cmd_string)


def load_cache():
    if not cache_path or not os.path.exists(cache_path):
        return

    with cache_lock:
        with open(cache_path, 'r', encoding='utf-8-sig') as fp:
            data = dict(json.load(fp))

        if data.get('working_directory') != working_directory:
            return

        if 'last_files' in data:
            last_files.clear()
            last_files.extend([x for x in data['last_files'] if os.path.exists(x)])


def save_cache():
    if not cache_path:
        return

    with cache_lock:
        data = {
            'working_directory': working_directory,
            'last_files': last_files,
        }

        with open(cache_path, 'w', encoding='utf-8') as fp:
            json.dump(data, fp)


# console script


def main():
    global outputfmt, max_segments, working_directory, cache_path

    parser = argparse.ArgumentParser(description='Grabs stream to segments using ffmpeg.')
    parser.add_argument('-i', '--input', help='input stream', required=True)
    parser.add_argument(
        '--input-args',
        help='replace ffmpeg arguments for input (use $$ to insert default) (default: "{}")'.format(default_input_args.replace('%', '%%')),
        default=default_input_args,
    )
    parser.add_argument(
        '--output-args',
        help='replace ffmpeg arguments for output (use $$ to insert default) (default: "{}")'.format(default_output_args.replace('%', '%%')),
        default=default_output_args,
    )
    parser.add_argument('-f', '--segment-format', help='segment format (default: mp4)', default='mp4')
    parser.add_argument('-o', '--output', help='output datetime pattern (default: %%Y-%%m-%%d_%%H-%%M-%%S.mp4)', default='%Y-%m-%d_%H-%M-%S.mp4')
    parser.add_argument('-t', '--duration', type=int, default=1200, help='segment duration in seconds (default: 1200; 20 min)')
    parser.add_argument('-s', '--segments', type=int, default=12, help='save only last N segments (0 - save all) (default: 12; 4 hours)')
    parser.add_argument('-c', '--ffmpeg-cmd', help='path to ffmpeg program (default: ffmpeg)', default='ffmpeg')
    parser.add_argument('-T', '--tmpfile', help='temporary json file where streamgrabber will store some cached information (e.g. last segments) (default: none)', default=None)
    parser.add_argument('-d', '--directory', help='directory where stream will be saved (default: current)', default='.')
    parser.add_argument('--printcmd', default=False, action='store_true', help='just print full ffmpeg command and exit')

    parser.add_argument(
        'commands',
        metavar='COMMAND',
        nargs='*',
        help='shell commands that will be called for each segment (path to segment will be added as last argument)',
    )

    args = parser.parse_args()
    working_directory = os.path.abspath(args.directory)
    cache_path = os.path.abspath(args.tmpfile) if args.tmpfile else None

    load_cache()

    ffmpeg_cmd = build_ffmpeg_cmd(
        stream=args.input,
        input_args=args.input_args,
        output_args=args.output_args,
        output=args.output,
        duration=args.duration,
        fmt=args.segment_format,
        ffmpeg_path=args.ffmpeg_cmd,
    )

    if args.printcmd:
        print(cmdlist_to_str(ffmpeg_cmd))
        return 0

    max_segments = max(0, args.segments)
    if max_segments > 0 and max_segments < 3:
        max_segments = 3

    outputfmt = args.output
    for x in args.commands:
        commands.append(shlex.split(x))

    prepare_watchdog()
    try:
        run_ffmpeg_forever(ffmpeg_cmd)
    finally:
        observer.stop()
        observer.join()

    return 0


if __name__ == '__main__':
    sys.exit(main())
