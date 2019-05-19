#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import gzip
from datetime import datetime, timedelta


def process_auth_line(oks_stat, fails_stat, line):
    '''Обрабатывает строку auth.log.

    :param dict oks_stat: словарь, в который будут складываться айпишники
      с успешной авторизацией
    :param dict fails_stat: словарь, в который будут складываться айпишники
      с неудачной авторизацией
    : param str line: собственно обрабатываемая строка
    '''

    # Образец обрабатываемой строки:
    # Dec  1 21:28:21 andreymal sshd[23152]: Failed password for root from 5.55.35.35 port 8800 ssh2

    line = line.strip()
    if not line:
        return
    lline = line.lower()

    month, day, tm = line.split()[:3]
    # В логах почему-то не записывается год, поэтому, считая, что логов
    # из далёкого прошлого или из будущего не бывает, подбираем год сами
    now = datetime.now()
    year = now.year
    while True:
        current_date = datetime.strptime('{} {} {} {}'.format(year, month, day, tm), '%Y %b %d %H:%M:%S')
        if current_date <= now:
            break
        year -= 1

    fail = False
    if ': failed password for ' in lline:
        fail = True
    elif ': accepted publickey for ' in lline:
        pass
    elif ': accepted password for ' in lline:
        pass
    elif 'accepted' in lline and 'invalid user accepted' not in lline:
        raise RuntimeError('Unexpected "Accepted" word in log')
    else:
        return

    line = line[line.find('for ') + 4:]
    if line.startswith('invalid user '):
        line = line[13:]

    user, line = line.rsplit(' from ', 1)
    ip = line.split(' ', 1)[0]

    stat = fails_stat if fail else oks_stat

    if ip not in stat:
        stat[ip] = {
            'count': 0,
            'usernames': set(),
            'last_date': None,
        }
    stat[ip]['count'] += 1
    stat[ip]['usernames'].add(user)
    if not stat[ip]['last_date'] or current_date > stat[ip]['last_date']:
        stat[ip]['last_date'] = current_date


def process_auth_log(paths, verbose=False):
    '''Парсит указанные auth.log файлы и возвращает два словаря: информацию
    об успешных и неуспешных авторизациях.

    :param list paths: список путей к файлам auth.log
    :param bool verbose: при True печатать процесс в stderr
    :rtype: (dict, dict)
    '''

    oks_stat = {}  # {ip: info_dict}
    fails_stat = {}

    for path in paths:
        if verbose:
            print('Processing {}...'.format(path), end=' ', file=sys.stderr)
            sys.stderr.flush()
        if path.endswith('.gz'):
            fp = gzip.open(path, 'rt', encoding='utf-8-sig')
        else:
            fp = open(path, 'r', encoding='utf-8-sig')
        with fp:
            for line in fp:
                process_auth_line(oks_stat, fails_stat, line)

        if verbose:
            print('done.', file=sys.stderr)

    return oks_stat, fails_stat


def sort_stat(stat, sort_by, reverse=True):
    if sort_by == 'latest':
        # sort by last date
        stat.sort(key=lambda x: x[1]['last_date'], reverse=reverse)
    elif sort_by == 'tries':
        # sort by tries count
        stat.sort(key=lambda x: x[1]['count'], reverse=reverse)
    else:
        raise ValueError('Unknown sorting method %r' % sort_by)


def print_formatted_stat(allstat, file=sys.stdout):
    for ip, stat in allstat:
        print(
            '{ip} ({count} tries as {usernames}; last {last})'.format(
                ip=ip,
                count=stat['count'],
                usernames=', '.join(sorted(stat['usernames'])),
                last=stat['last_date'].strftime('%Y-%m-%d %H:%M:%S'),
            ),
            file=file,
        )


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Parses auth.log files and prints success and fail statistics per IP.')
    parser.add_argument('paths', metavar='/path/to/auth.log', type=str, nargs='*', default=['/var/log/auth.log'], help='Path to auth.log file (by default /var/log/auth.log)')
    parser.add_argument('--since', help='show stat for last date greater than this (localtime, format: "%%Y-%%m-%%dT%%H:%%M:%%S")')
    parser.add_argument('--mintries-failed', type=int, help='show stat of failed tries for last date equal or greater than this tries count')
    parser.add_argument('--mintries-ok', type=int, help='show stat of successful tries for last date equal or greater than this tries count')
    parser.add_argument('-s', '--sort', action='store', choices=['tries', 'latest'], default='tries', help='select field for sorting')
    parser.add_argument('-a', '--asc', action='store_true', help='sort ascending instead of descending')
    parser.add_argument('-i', '--onlyip', action='store_true', help='print only failed ips (good for scripts; success ips are not printed)')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output (uses stderr)')

    args = parser.parse_args(sys.argv[1:])

    paths = args.paths
    sort_by = args.sort
    sort_reverse = not args.asc
    verbose = args.verbose
    since = args.since
    mintries_failed = args.mintries_failed
    mintries_ok = args.mintries_ok
    onlyip = args.onlyip
    del parser, args

    if since:
        if since == 'today':
            since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif since == 'yesterday':
            since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            since -= timedelta(days=1)
        else:
            since = datetime.strptime(since.strip().replace('T', ' '), '%Y-%m-%d %H:%M:%S')

    oks, fails = process_auth_log(paths, verbose=verbose)
    oks = list(oks.items())
    fails = list(fails.items())

    if since:
        oks = [x for x in oks if x[1]['last_date'] >= since]
        fails = [x for x in fails if x[1]['last_date'] >= since]

    if mintries_failed:
        fails = [x for x in fails if x[1]['count'] >= mintries_failed]

    if mintries_ok:
        oks = [x for x in oks if x[1]['count'] >= mintries_ok]

    if verbose:
        print('Sorting...', file=sys.stderr)

    sort_stat(oks, sort_by, reverse=sort_reverse)
    sort_stat(fails, sort_by, reverse=sort_reverse)

    if verbose:
        print('', file=sys.stderr)

    if onlyip:
        for ip, _ in fails:
            print(ip)

    else:
        if fails:
            print('Failed:')
            print_formatted_stat(fails)
            if oks:
                print()

        if oks:
            print('Success:')
            print_formatted_stat(oks)

    return 0


if __name__ == '__main__':
    sys.exit(main())
