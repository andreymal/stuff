import array
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from datetime import datetime

from tabun_stat import types, utils
from tabun_stat.datasource.base import DataNotFound
from tabun_stat.processors.base import BaseProcessor


@dataclass
class WordStat:
    __slots__ = (
        'first_date',
        'first_public_date',
        'last_date',
        'last_public_date',
        'count',
        'public_count',
        'nobots_count',
        'public_nobots_count',
        'users',
        'users_count',
        'public_users',
        'public_users_count',
    )

    first_date: datetime
    first_public_date: Optional[datetime]
    last_date: datetime
    last_public_date: Optional[datetime]
    count: int
    public_count: int
    nobots_count: int
    public_nobots_count: int

    # Списки/массивы медленнее, но экономнее по памяти чем словари и множества,
    # поэтому городим такие компромиссные костыли
    users: Dict[int, 'array.array[int]']
    users_count: int
    public_users: Dict[int, 'array.array[int]']
    public_users_count: int

    def put_user(self, user_id: int) -> None:
        user_key = user_id // 1000
        user_list = self.users.get(user_key)
        if user_list is None:
            self.users[user_key] = array.array('I', [user_id])
            self.users_count += 1
        elif user_id not in user_list:
            user_list.append(user_id)
            self.users_count += 1

    def put_public_user(self, user_id: int) -> None:
        user_key = user_id // 1000
        user_list = self.public_users.get(user_key)
        if user_list is None:
            self.public_users[user_key] = array.array('I', [user_id])
            self.public_users_count += 1
        elif user_id not in user_list:
            user_list.append(user_id)
            self.public_users_count += 1



class WordsProcessor(BaseProcessor):
    default_delimeters = '.,?!@\'"«»-—–()*:;#№$%^&[]{}\\/|`~=©®™+©°×⋅…_″′“”'

    # Так как я решил использовать байтовые строки вместо юникодных, придётся
    # предварительно заменить все юникодные пробельные символы на обычный пробел,
    # чтобы split нормально отработал
    whitespaces = '\x09\x0a\x0b\x0c\x0d\x1c\x1d\x1e\x1f\x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000'

    def __init__(self, bot_ids: Iterable[int] = (), delimeters: Optional[str] = None) -> None:
        super().__init__()
        self.bot_ids = tuple(bot_ids)
        self.delimeters = delimeters or self.default_delimeters

        self._trans_table = str.maketrans({x: 32 for x in self.delimeters + self.whitespaces})

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
        # {первые три байта: {слово: WordStat}}
        self._stat: Dict[bytes, Dict[bytes, WordStat]] = {}
        self._words_list: List[bytes] = []

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

    def _get_word_stat(self, word: bytes) -> Optional[WordStat]:
        word_key = word[:3]
        words_stat_local = self._stat.get(word_key)
        if words_stat_local is None:
            return None
        return words_stat_local.get(word)

    def _put_word_stat(self, word: bytes, stat: WordStat) -> None:
        word_key = word[:3]
        words_stat_local = self._stat.get(word_key)
        if words_stat_local is None:
            self._stat[word_key] = {word: stat}
        else:
            words_stat_local[word] = stat

    def _process(self, author_id: int, raw_body: str, created_at_local: datetime, is_comment: bool, blog_status: int) -> None:
        assert self.stat

        # Фиксим косяк старых версий tbackup
        if raw_body.startswith('<div ') and raw_body.endswith('</div>'):
            raw_body = raw_body[raw_body.find('>') + 1:raw_body.rfind('<')].strip()

        body = raw_body.strip()
        if not body:
            return

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
        # (хранить в закодированном utf-8 немного экономнее по памяти и чуть быстрее по скорости)
        body = body.translate(self._trans_table)
        words = body.lower().encode('utf-8').split()

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
        if not is_bot and author_id == 36492 and len(words) > 3 and words[0] == b'\xd0\xb2\xd1\x81\xd0\xb5\xd0\xb3\xd0\xbe' and words[2].startswith(b'\xd0\xba\xd0\xbe\xd0\xbc\xd0\xbc\xd0\xb5\xd0\xbd\xd1\x82\xd0\xb0\xd1\x80'):
            # MineOzelot статистика в бункере
            is_bot = True

        for word in words:
            ws = self._get_word_stat(word)
            if ws is None:
                self._words_list.append(word)
                ws = WordStat(
                    first_date=created_at_local,
                    first_public_date=None,
                    last_date=created_at_local,
                    last_public_date=None,
                    count=0,
                    public_count=0,
                    nobots_count=0,
                    public_nobots_count=0,
                    users={},
                    users_count=0,
                    public_users={},
                    public_users_count=0,
                )
                self._put_word_stat(word, ws)

            is_public = blog_status in (0, 2)

            if ws.first_public_date is None and is_public:
                ws.first_public_date = created_at_local

            ws.last_date = created_at_local
            ws.count += 1
            if not is_bot:
                ws.nobots_count += 1
            ws.put_user(author_id)

            if is_public:
                ws.last_public_date = created_at_local
                ws.public_count += 1
                if not is_bot:
                    ws.public_nobots_count += 1
                ws.put_public_user(author_id)

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
                data = self._get_word_stat(word)
                assert data is not None

                if data.users_count < 20:
                    users = [
                        self.stat.source.get_username_by_user_id(uid)
                        for user_list in data.users.values()
                        for uid in user_list
                    ]
                else:
                    users = []

                if data.public_users_count < 20:
                    public_users = [
                        self.stat.source.get_username_by_user_id(uid)
                        for user_list in data.public_users.values()
                        for uid in user_list
                    ]
                else:
                    public_users = []

                fp.write(utils.csvline(
                    word.decode('utf-8'),
                    data.first_date,
                    data.first_public_date or '',
                    data.last_date,
                    data.last_public_date or '',
                    data.count,
                    data.public_count,
                    data.nobots_count,
                    data.public_nobots_count,
                    data.users_count,
                    '; '.join(sorted(users)) if users else '',
                    data.public_users_count,
                    '; '.join(sorted(public_users)) if public_users else '',
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
