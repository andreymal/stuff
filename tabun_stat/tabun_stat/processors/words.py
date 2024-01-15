import os
from typing import Dict, Any, Iterable, List
from datetime import datetime

from tabun_stat import types, utils
from tabun_stat.datasource.base import DataNotFound
from tabun_stat.processors.base import BaseProcessor


class WordsProcessor(BaseProcessor):
    def __init__(self, bot_ids: Iterable[int] = (), delimeters: str = '.,?!@\'"«»-—–()*:;#№$%^&[]{}\\/|`~=©®™+©°×⋅…_″′“”') -> None:
        super().__init__()
        self.bot_ids = tuple(bot_ids)
        self.delimeters = delimeters

        # Первый элемент — значение в штуках/символах/байтах, второй — количество постов/комментов
        self._post_len_words = [0, 0]
        self._post_len_chars = [0, 0]
        self._post_len_bytes = [0, 0]

        # Для комментов аналогично
        self._comment_len_words = [0, 0]
        self._comment_len_chars = [0, 0]
        self._comment_len_bytes = [0, 0]

        # Комменты-смайлы и прочий флуд без слов
        self._comments_without_text = 0

        # Статистика по отдельным словам
        # {первые две буквы: {слово: {словарь статистики}}}
        self._stat = {}  # type: Dict[str, Dict[str, Dict[str, Any]]]
        self._words_list = []  # type: List[str]

    def process_post(self, post: types.Post) -> None:
        assert post.created_at_local is not None
        self._process(post.author_id, post.body, post.created_at_local, is_comment=False, blog_status=post.blog_status)

    def process_comment(self, comment: types.Comment) -> None:
        assert comment.created_at_local is not None
        assert self.stat

        try:
            if comment.post_id is None:
                raise DataNotFound
            blog_id = self.stat.source.get_blog_id_of_post(comment.post_id)
        except DataNotFound:
            self.stat.log(0, f'WARNING: words: comment {comment.id} for unknown post {comment.post_id}')
            return

        blog_status = self.stat.source.get_blog_status_by_id(blog_id)
        self._process(comment.author_id, comment.body, comment.created_at_local, is_comment=True, blog_status=blog_status)

    def _process(self, author_id: int, raw_body: str, created_at_local: datetime, is_comment: bool, blog_status: int) -> None:
        assert self.stat

        # Фиксим косяк старых версий tbackup
        if raw_body.startswith('<div ') and raw_body.endswith('</div>'):
            raw_body = raw_body[raw_body.find('>') + 1:raw_body.rfind('<')].strip()

        body = raw_body.strip()
        if not body:
            return

        username = self.stat.source.get_username_by_user_id(author_id)

        # Выкидываем HTML-теги
        while True:
            f1 = body.find('<')
            if f1 < 0:
                break
            f2 = body.find('>', f1 + 1)
            if f2 < 0:
                break
            body = body[:f1] + ' ' + body[f2 + 1:]

        # Делим сообщение на слова
        for c in self.delimeters:
            body = body.replace(c, ' ')
        words = body.lower().split()

        # Считаем статистику публикаций в целом
        if not is_comment:
            self._post_len_words[0] += len(words)
            self._post_len_chars[0] += len(raw_body)
            self._post_len_bytes[0] += len(raw_body.encode('utf-8'))
            self._post_len_words[1] += 1
            self._post_len_chars[1] += 1
            self._post_len_bytes[1] += 1
        else:
            self._comment_len_words[0] += len(words)
            self._comment_len_chars[0] += len(raw_body)
            self._comment_len_bytes[0] += len(raw_body.encode('utf-8'))
            self._comment_len_words[1] += 1
            self._comment_len_chars[1] += 1
            self._comment_len_bytes[1] += 1

        if is_comment and not words:
            self._comments_without_text += 1

        # Считаем статистику отдельных слов
        is_bot = author_id in self.bot_ids  # am31, lunabot, ozibot
        if not is_bot and author_id == 36492 and len(words) > 3 and words[0] == 'всего' and words[2].startswith('комментар'):
            # MineOzelot статистика в бункере
            is_bot = True

        for word in words:
            if word[:2] not in self._stat:
                self._stat[word[:2]] = {}
            words_stat_local = self._stat[word[:2]]

            try:
                ws = words_stat_local[word]
            except KeyError:
                self._words_list.append(word)
                ws = {}
                ws = {
                    'first_date': created_at_local,
                    'first_public_date': None,
                    'last_date': None,
                    'last_public_date': None,
                    'count': 0,
                    'public_count': 0,
                    'nobots_count': 0,
                    'public_nobots_count': 0,
                    'users': set(),
                    'public_users': set(),
                }
                words_stat_local[word] = ws

            is_public = blog_status in (0, 2)

            if ws['first_public_date'] is None and is_public:
                ws['first_public_date'] = created_at_local

            ws['last_date'] = created_at_local
            ws['count'] += 1
            if not is_bot:
                ws['nobots_count'] += 1
            ws['users'].add(username)

            if is_public:
                ws['last_public_date'] = created_at_local
                ws['public_count'] += 1
                if not is_bot:
                    ws['public_nobots_count'] += 1
                ws['public_users'].add(username)

    def stop(self) -> None:
        assert self.stat

        with open(os.path.join(self.stat.destination, 'words.csv'), 'w', encoding='utf-8') as fp:
            fp.write(utils.csvline(
                'Слово',
                'Первое исп-е',
                'Первое исп-е на внешке',
                'Последнее исп-е',
                'Последнее исп-е на внешке',
                'Сколько раз',
                'Сколько раз на внешке',
                'Сколько раз (без ботов)',
                'Сколько раз на внешке (без ботов)',
                'Сколько юзеров юзали',
                'Кто юзал',
                'Сколько юзеров юзали на внешке',
                'Кто юзал на внешке'
            ))
            for word in self._words_list:
                data = self._stat[word[:2]][word]
                fp.write(utils.csvline(
                    word,
                    data['first_date'],
                    data['first_public_date'] or '',
                    data['last_date'],
                    data['last_public_date'] or '',
                    data['count'],
                    data['public_count'],
                    data['nobots_count'],
                    data['public_nobots_count'],
                    len(data['users']),
                    '; '.join(sorted(data['users'])) if len(data['users']) < 20 else '',
                    len(data['public_users']),
                    '; '.join(sorted(data['public_users'])) if len(data['public_users']) < 20 else '',
                ))

        with open(os.path.join(self.stat.destination, 'avgstats.txt'), 'w', encoding='utf-8') as fp:
            fp.write('Средняя длина поста: {} слов, {} символов, {} байт\n'.format(
                int(self._post_len_words[0] / self._post_len_words[1]) if self._post_len_words[1] != 0 else 0,
                int(self._post_len_chars[0] / self._post_len_chars[1]) if self._post_len_chars[1] != 0 else 0,
                int(self._post_len_bytes[0] / self._post_len_bytes[1]) if self._post_len_bytes[1] != 0 else 0,
            ))
            fp.write('Средняя длина коммента: {} слов, {} символов, {} байт\n'.format(
                int(self._comment_len_words[0] / self._comment_len_words[1]) if self._comment_len_words[1] != 0 else 0,
                int(self._comment_len_chars[0] / self._comment_len_chars[1]) if self._comment_len_chars[1] != 0 else 0,
                int(self._comment_len_bytes[0] / self._comment_len_bytes[1]) if self._comment_len_bytes[1] != 0 else 0,
            ))
            fp.write('Комментов без текста: {}\n'.format(self._comments_without_text))

        super().stop()
