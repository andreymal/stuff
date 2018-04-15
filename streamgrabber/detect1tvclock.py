#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shlex
import shutil
import argparse
from io import BytesIO
from subprocess import Popen, PIPE, DEVNULL

from PIL import Image, ImageFilter


size = (640, 360)

clock_color_from = (69, 101, 149)
clock_color_to = (164, 189, 220)


# Координаты границ чисел с сжатом формате hex, чтобы визуально места меньше занимало:
# два байта на икс, два байта на игрек — по восемь hex-символов на координату.
# Этот набор получился так:
# 1) сперва высчитана усреднённая картинка с границами для имеющегося в запасе видео: https://i.imgur.com/ruXjewl.png
# 2) потом убраны мусор и сомнительные пиксели вручную в гимпе: https://i.imgur.com/FT6onRR.png
# 3) картинка поделена на 12 групп, по группе на каждое число
# 4) и для экономии места взят каждый четвёртый пиксель и закодирован в приведённый ниже hex: https://i.imgur.com/jqQBnAP.png
edge_groups_raw = [
    # 1
    '018e00440192004401960044019a0044019e004401a2004401a6004401aa0044018e0046018e0048018e004a018e004c0193004c0197004c01aa004c0191004d'
    '0195004d0199004d019c004f019c0051019c0053019c0055019c0057019c0059019c005b019c005d019c005f019c0061019e006201a2006201a6006201aa0062',
    # 2
    '01e0004401e4004401e8004401ec004401f0004401f4004401f8004401fc0044020000440203004501e0004602090047020b004901e0004b01e2004c01e6004c'
    '01ea004c01ee004c01f2004c01f6004c01fa004c020c004c020c004e01f90050020b005001f8005101f3005201ee0053020900530205005401e7005502030055'
    '01e400560200005601fa005701f5005801f0005901e0005a01ef005c01f3005c01f7005c01fb005c01ff005c0203005c0207005c020b005c020b005e020b0060',
    # 3
    '01e000a501ec00a501f000a501f400a501f800a501fc00a5020000a5020800a701e000ac020b00af01eb00b1020900b6020b00b9020b00bc020900c101e200c3',
    # 4
    '01fb010601ff01060203010602070106020b010601f7010801f60109020b010a01ef010c01ee010d01fc010e01ea010f020b010f01f9011001e60111020b0111'
    '0200011201f3011301f0011401df011501df011601f0011701f4011701f8011701fc0117020f01170210011801df011a01df011c01e0011e01e4011e01e8011e',
    # 5
    '0185010601890106018d0106019101060195010601990106019d010601a1010601a5010601a9010601ad010601b1010601b1010801b1010a01b1010c0196010d'
    '019a010d019e010d01a7010d01ab010d01af010d0185011001850114018501160185011801b2011901b2011c0185011e018501200185012201aa012301860124',
    # 6
    '0132010601360106013a0106013e01060142010601460106014a0106014e01060152010601560106012d0108015601090156010b0137010d013b010d0140010d'
    '0149010d014d010d0151010d0155010d01290110013f0111014d0112015001130129011501290117012901190129011b0156011c0156011e012c0121012f0123',
    # 7
    '00d0010600d4010600d8010600dc010600e0010600e4010600e8010600ec010600f0010600f4010600d0010700d0010900d0010b00d0010d00d5010d00d9010d',
    # 8
    '007a0106007e01060082010600860106008a0106008e0106009201060096010600780107009c0107009d0108009e010a0074010c0082010d0086010d008a010d'
    '008e010d0092010d0074010f007f01100082011100860111008a0111008e011100920111009e011200780114007501180074011a00a0011b00a0011d00740120',
    # 9
    '007b00a5007f00a5008300a5008700a5008b00a5008f00a5009300a5009700a5007b00a6009b00a6009c00a7007500a9009f00aa008000ac008400ac008800ac'
    '008c00ac009000ac009f00ac009400ad007f00ae007f00af007f00b0008400b0008800b0008c00b0009000b0007400b1008400b1008800b1008c00b1009000b1'
    '007400b2007600b300a000b4007900b6007b00b7007f00b7008300b7008700b7008b00b7008f00b700a000b7008100b8008500b8008900b8008d00b8009100b8'
    '009400b9007400bb007400bc007800bc007c00bc008000bc008400bc008800bc008c00bc009000bc009f00bc007400be009d00bf009d00c0009c00c1009a00c2',
    # 10
    '0066004400930044008d004500b10045008100460066004700b6004700b7004800b800490089004a0088004b0088004c009a004c009e004c00a2004c00a6004c'
    '00b9004c0088004d0081004e00b9004e0095004f0081005000b90050009500510081005200b90052009500530081005400b90054009500550081005600b90056'
    '009500570081005800b90058009500590081005a0074005b0098005b009c005b00a0005b00a4005b00a8005b0074005c0074005d0074005e0074005f00740060',
    # 11
    '00c9004400d1004400d5004400db004400df004400e4004400ef004400f4004400f8004400fe0044010300440107004400e5004500e5004600e5004700e50048'
    '00e5004900e5004a00e5004b00e5004c00cd004d00e5004d00f8004d00fb004e00fb004f00fb0050010800510108005200d7005400e5005500e5005600fb0057',
    # 12
    '01180044011e00440122004401270044012c004401300044013d00440143004401470044014c00440150004401540044015a004401180045013d004501610045'
    '01620046013c0047013c0048013c0049013c004a013c004b0119004c013f004c0143004c0147004c014b004c014f004c0153004c0157004c0119004d011e004d'
    '0124004d0127004e0127004f0166004f01550050012700510152005101270052014f00520134005301630053014500540160005401340055015c005501270056'
    '0159005601340057015500570134005801520058013c0059014e0059013c005a0127005c014b005c014f005c0153005c0157005c015b005c015f005c0163005c'
    '0127005d0127005e0127005f0127006001270061012f0062013c00620142006201460062014a0062014e00620152006201560062015a0062015e006201620062',
]

edge_groups = []
for edge_group_raw in edge_groups_raw:
    edge_group = []
    for gi in range(len(edge_group_raw) // 8):
        gi = gi * 8
        edge_group.append((
            int(edge_group_raw[gi:gi + 4], 16),
            int(edge_group_raw[gi + 4:gi + 8], 16),
        ))
    edge_groups.append(edge_group)


class Video:
    def __init__(self, path, frame_step=50, threshold=3, fps=25, debug_directory=None):
        '''Экземпляр анализируемого видео, содержащий всякую мету.

        :param str path: путь к видеофайлу
        :param int frame_step: проверять только каждый ``frame_step`` кадр
        :param int threshold: считать успехом только нахождение ``threshold`` часов подряд
        :param int fps: частота кадров видео (используется только для вывода информации)
        :param str debug_directory: каталог для сохранения отладочной информации
        '''
        self.path = path
        self.frame_step = int(frame_step)
        self.threshold = int(threshold)
        self.fps = int(fps)
        self.debug_directory = debug_directory

        self.success = False
        self.detected_frames = []

        self.last_frames = []
        self.last_frames_max_count = 2

        if not os.path.isfile(path):
            raise ValueError('File {!r} not found'.format(path))


class Frame:
    def __init__(self, framedata, frameno=0, debug_directory=None):
        if len(framedata) != size[0] * size[1] * 3:
            raise ValueError

        self.framedata = framedata
        self.frameno = int(frameno)
        self.debug_directory = debug_directory

        self._im = None
        self._edges_im = None
        self._debug_im = None

        self.debug_files = {}  # {name_postfix: bytes}

    def __del__(self):
        self.close()

    def close(self):
        if self._im:
            self._im.close()
            self._im = None

        if self._edges_im:
            self._edges_im.close()
            self._edges_im = None

        if self._debug_im:
            self._debug_im.close()
            self._debug_im = None

    @property
    def im(self):
        if self._im is None:
            self._im = Image.frombytes('RGB', size, self.framedata)
        return self._im

    @property
    def edges_im(self):
        if self._edges_im is None:
            self._edges_im = self.im.filter(ImageFilter.FIND_EDGES)
        return self._edges_im

    @property
    def debug_im(self):
        if not self.debug_directory:
            return None
        if self._debug_im is None:
            self._debug_im = self.im.copy()
        return self._debug_im


def frame_test_avg_blue(video, frame, verbose=0):
    '''Тест кадра на наличие часов: проверка, что картинка достаточно синяя.

    :param Video video: анализируемое видео
    :param Frame frame: анализируемый кадр
    :param int verbose: уровень флуда в stderr (здесь не используется)
    '''

    rgb = frame.im.resize((1, 1), Image.BILINEAR).getdata()[0]
    if not (
        rgb[0] >= clock_color_from[0] and rgb[0] <= clock_color_to[0] and
        rgb[1] >= clock_color_from[1] and rgb[1] <= clock_color_to[1] and
        rgb[2] >= clock_color_from[2] and rgb[2] <= clock_color_to[2]
    ):
        return False
    if rgb[0] - rgb[2] > 8 or rgb[1] - rgb[2] > 8:
        return False
    return None  # не любая синяя картинка это часы


def frame_test_only_blue(video, frame, verbose=0):
    # Когда снимают снег, все точки белые; проверяем более точно, что
    # картинка синяя: откровенно красных-зелёных пикселей быть не должно
    # (логотип новостей, люди и т.п.)
    small = frame.im.resize((64, 64), Image.BILINEAR)
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
    return None


def frame_test_edges(video, frame, verbose=0):
    '''Тест кадра на наличие часов: определение наличия цифр по их границам.

    :param Video video: анализируемое видео
    :param Frame frame: анализируемый кадр
    :param int verbose: уровень флуда в stderr
    '''

    ok_groups = 0
    ok_all = 0

    # Здесь была попытка смешивания с предыдущими кадрами,
    # но ложноположительных срабатываний меньше не стало
    '''prev_frames_count = 2
    min_frameno = prev_frames_count * video.frame_step

    if len(video.last_frames) >= prev_frames_count:
        ims = [x.im for x in video.last_frames[-prev_frames_count:]] + [frame.im]
        edges_im = ims[0].copy()
        for i, im in enumerate(ims[1:], 1):
            with edges_im:
                edges_im = Image.blend(edges_im, im, 1.0 / float(i + 1))
        with edges_im:
            if frame.debug_directory:
                frame.debug_files['_avg.bmp'] = image2string(edges_im)
            edges_im = edges_im.filter(ImageFilter.FIND_EDGES)
    else:
        if frame.frameno < min_frameno:
            return False
        edges_im = frame.edges_im.copy()'''

    with frame.edges_im.copy() as edges_im:
        # Перебираем каждую группу цифр по отдельности
        for group in edge_groups:
            ok = 0
            ok_pixels = []

            # Перебираем каждый известный пиксель границы в группе
            for x, y in group:
                rgb = edges_im.getpixel((x, y))
                # Если пиксель на edges_im явно не чёрный, значит тут граница
                if max(rgb) >= 100:
                    ok += 1
                    ok_all += 1
                    ok_pixels.append((x, y))

            # Если нашлась хотя бы треть точек, соответствующих границам цифр,
            # то считаем, что цифру успешно нашли
            if ok >= len(group) // 3:
                ok_groups += 1

            # Для отладки подсвечиваем что нашли. Красным — просто найденные точки,
            # синим — точки из успешных групп
            if frame.debug_im:
                for xy in ok_pixels:
                    frame.debug_im.putpixel(xy, (0, 255, 0) if ok >= len(group) // 3 else (255, 0, 0))

        if frame.debug_directory:
            frame.debug_files['_edge.bmp'] = image2string(edges_im)

    # Нашли шесть групп чисел — успех
    success = ok_groups >= 6

    # Флудим в stderr
    if verbose >= 2:
        print('/ {}/{} {}/{}'.format(
            ok_all, sum(len(x) for x in edge_groups),
            ok_groups, len(edge_groups),
        ), end=' ', file=sys.stderr)


    return success


def build_ffmpeg_cmd(cmd, path, step):
    result = shlex.split(cmd)

    result.extend(('-loglevel', 'panic', '-threads', '1'))
    result.extend(('-r', str(step), '-i', path, '-q:v', '1'))
    result.extend(('-vf', 'select=not(mod(n\\,{step})),scale={w}:{h}'.format(step=step, w=size[0], h=size[1])))
    result.extend(('-r', '1', '-c:v', 'rawvideo', '-pix_fmt', 'rgb24', '-f', 'image2pipe', '-'))

    return result


def is_clock_frame(video, frame, verbose=0):
    '''Пытается определить, есть ли на кадре часы Первого канала.

    :param Video video: анализируемое видео
    :param Frame frame: анализируемый кадр
    :param int verbose: уровень флуда в stderr
    :rtype: bool
    '''

    if verbose >= 2:
        print(frame2tm(frame.frameno, video.fps), end=' ', file=sys.stderr, flush=True)

    success = False

    # Запускаем все тесты, проверяющие наличие или отсутствие часов на кадре
    # - тест вернул True — точно часы, прерываем работу
    # - тест вернул False — точно не часы, прерываем работу
    # - тест вернул None — ну хрен знает, продолжаем запускать тесты дальше
    for test in [frame_test_only_blue, frame_test_edges]:
        result = test(video, frame, verbose=verbose)
        if result is True:
            success = True
            break
        if result is False:
            success = False
            break
        else:
            assert result is None

    # Сохраняем отладочную картинку
    if video.debug_directory and frame.debug_im:
        ok_str = 'ok' if success else 'no'
        prefix = '%07d_%s' % (frame.frameno, ok_str)
        frame.debug_im.save(os.path.join(video.debug_directory, prefix + '.bmp'))

        # И отладочные файлы
        for postfix, data in frame.debug_files.items():
            with open(os.path.join(video.debug_directory, prefix + postfix), 'wb') as fp:
                fp.write(data)

    if verbose >= 2:
        print(('/ OK' if success else ''), file=sys.stderr)

    return success


def find_clock_frames_in_video(video, verbose=0, stop_on_success=False, cmd='ffmpeg'):
    '''Ищет часы в указанном видеофайле. Возвращает кортеж с двумя элементами:
    bool — успех/неуспех и список номеров кадров, на которых вроде бы часы.

    :param Video video: анализируемое видео
    :param int verbose: уровень флуда в stderr
    :param bool stop_on_success: если True, то прекращает анализ сразу после первого успеха
    :param str cmd: команда и параметры ffmpeg
    '''

    if verbose >= 1:
        print('Clock detector: processing', video.path, file=sys.stderr)

    # Собираем команду ffmpeg
    run_cmd = build_ffmpeg_cmd(cmd, video.path, video.frame_step)

    # Запускаем его
    ffmpeg = Popen(run_cmd, shell=False, stdin=PIPE, stdout=PIPE)

    framesize = size[0] * size[1] * 3

    frameno = -video.frame_step
    ok = 0
    video.detected_frames = []
    video.success = False
    while True:
        # Читаем из ffmpeg по кадру
        framedata = ffmpeg.stdout.read(framesize)
        frameno += video.frame_step
        if not framedata:
            break
        assert len(framedata) == framesize

        frame = Frame(framedata, frameno, debug_directory=video.debug_directory)

        # Проверяем, есть ли часы на кадре
        if is_clock_frame(video, frame, verbose=verbose):
            # Если есть — запоминаем
            ok += 1
            video.detected_frames.append(frameno)
            # Если есть нужное число часов подряд, то успех
            video.success = video.success or ok >= video.threshold
            # Если просят остановиться при успехе, останавливаемся
            if video.success and stop_on_success:
                ffmpeg.stdin.write(b'q')
                ffmpeg.stdin.flush()
                ffmpeg.stdout.read()  # flush buffer to prevent deadlock
                break
        else:
            # Не часы — сбрасываем счётчик подряд идущих часов
            ok = 0

        video.last_frames = video.last_frames[-video.last_frames_max_count:] + [frame]

    if ffmpeg.wait() != 0:
        raise RuntimeError('ffmpeg exited with non-zero code')

    if verbose >= 1:
        if video.success:
            print('Success! Found {} frames'.format(len(video.detected_frames)), file=sys.stderr)
        elif video.detected_frames:
            print('Found {} frames, but this is too few for success'.format(len(video.detected_frames)), file=sys.stderr)
        else:
            print('Clock frames not found', file=sys.stderr)


def apply_action(video, action, target_directory=None, verbose=0):
    '''Применяет действие по помещению видеофайла с найденными часами
    в указанный каталог. Доступные действия: notice (ничего не делает), copy,
    hardlink, symlink, move.

    :param Video video: анализируемое видео
    :param str action: выполняемое действие
    :param str target_directory: каталог, в который поместить видеофайл
    :param bool verbose: если больше нуля, выводить лог в консоль
    '''

    if action == 'notice':
        return
    assert video.detected_frames
    assert os.path.isdir(target_directory)

    at = frame2tm(video.detected_frames[0], video.fps)

    new_name, ext = os.path.splitext(os.path.split(video.path)[1])
    new_name = new_name + '__at_' + at.replace(':', '-') + ext
    new_path = os.path.join(target_directory, new_name)

    if action == 'copy':
        if verbose:
            print('Copying video to {}...'.format(new_name), end=' ', file=sys.stderr, flush=True)
        shutil.copy2(video.path, new_path)
        if verbose:
            print('Done.', file=sys.stderr)

    elif action == 'hardlink':
        if verbose:
            print('Hardlink video to {}'.format(new_name), file=sys.stderr)
        os.link(video.path, new_path)

    elif action == 'symlink':
        if verbose:
            print('Symlink video to {}'.format(new_name), file=sys.stderr)
        link_to = os.path.relpath(video.path, os.path.dirname(new_path))
        os.symlink(link_to, new_path)

    elif action == 'move':
        if verbose:
            print('Moving video to {}'.format(new_name), file=sys.stderr)
        os.rename(video.path, new_path)


def frame2tm(f, fps=25):
    tm = f // fps
    m = tm // 60
    s = tm % 60
    return '{:02d}:{:02d}'.format(m, s)


def image2string(im, format='BMP', **kwargs):
    fp = BytesIO()
    im.save(fp, format=format, **kwargs)
    return fp.getvalue()


def main():
    parser = argparse.ArgumentParser(description='Copies/moves video files with 1tv clock to target directory')
    parser.add_argument('-d', '--directory', help='target directory')
    parser.add_argument('-D', '--debug-directory', help='directory where debug frames will be saved')
    parser.add_argument('-m', '--mode', default='notice', choices=('notice', 'copy', 'hardlink', 'symlink', 'move'), help='what to do with found video (copy, hardlink, symlink, move; default: notice)')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='-v: print results to stdout; -vv: print debug output')
    parser.add_argument('-f', '--frame-step', default=50, type=int, help='step between analyzed frames (default: 50)')
    parser.add_argument('-r', '--fps', default=25, type=int, help='frames per second in input video (used only for seconds formatting; default: 25)')
    parser.add_argument('-F', '--failure-if-not-found', default=False, action='store_true', help='exit with non-zero code if clock is not found')
    parser.add_argument('-S', '--stop-on-success', default=False, action='store_true', help='stop video processing after first success')
    parser.add_argument('-t', '--threshold', default=3, type=int, help='minimum frames count to detect clock (default: 3)')
    parser.add_argument('-c', '--cmd', default='ffmpeg', help='ffmpeg command and input arguments')
    parser.add_argument('-C', '--success-cmd', help='run custom command for success video (path will be added as last argument)')

    parser.add_argument(
        'videos',
        metavar='VIDEO',
        nargs='+',
        help='path to video files',
    )

    args = parser.parse_args()

    target_directory = None
    if args.mode != 'notice':
        if not args.directory:
            print('Target directory is required', file=sys.stderr)
            return 2
        target_directory = os.path.abspath(args.directory)
        if not os.path.isdir(target_directory):
            os.makedirs(target_directory)

    debug_directory = None
    if args.debug_directory:
        debug_directory = os.path.abspath(args.debug_directory)
        if not os.path.isdir(debug_directory):
            os.makedirs(debug_directory)

    success = False

    for path in args.videos:
        video = Video(
            path,
            frame_step=args.frame_step,
            threshold=args.threshold,
            fps=args.fps,
            debug_directory=debug_directory,
        )

        find_clock_frames_in_video(
            video,
            verbose=args.verbose,
            stop_on_success=args.stop_on_success,
            cmd=args.cmd,
        )
        success = success or video.success

        if video.success:
            if args.success_cmd:
                if Popen(shlex.split(args.success_cmd) + [path], shell=False, stdin=DEVNULL).wait() != 0:
                    print('Custom command exited with non-zero code', file=sys.stderr)
                    return 1
            apply_action(
                video,
                args.mode,
                target_directory=target_directory,
                verbose=args.verbose,
            )

    return 0 if success or not args.failure_if_not_found else 1


if __name__ == '__main__':
    sys.exit(main())
