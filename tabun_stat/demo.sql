BEGIN TRANSACTION;


CREATE TABLE users(
    id int not null primary key,
    username varchar(32) not null,
    realname text default null,
    skill real not null,
    rating real not null,
    gender char(1) default null,
    birthday date default null,
    registered_at datetime not null,
    description mediumtext default null
);

INSERT INTO users VALUES(1,'Random',NULL,12879.07,5495.64,NULL,NULL,'1969-12-31 22:00:00',NULL);
INSERT INTO users VALUES(5,'Constrictor','Многорукий Удав',692.37,451.91,'M',NULL,'2011-08-13 13:06:00',NULL);
INSERT INTO users VALUES(6,'GaPAoT','GaPAoT',36439.26,13101.72,'M','1990-07-29','2011-08-13 13:09:00','Глава Секты Великой Трикси');
INSERT INTO users VALUES(7,'Orhideous','Андрій Кушнір (Orhideous)',83428.76,31326.65,'M','1993-04-17','2011-08-13 13:14:00','Технопегас');
INSERT INTO users VALUES(10,'FrownyFrog',NULL,2.12,26.6,'M','1993-07-04','2011-08-13 13:49:00',NULL);
INSERT INTO users VALUES(11,'McGyver',NULL,304.62,174.71,'M','1992-04-13','2011-08-13 13:50:00',NULL);
INSERT INTO users VALUES(14,'Nekit1234007',NULL,7501.92,2765.98,'M',NULL,'2011-08-13 13:56:00',NULL);
INSERT INTO users VALUES(47,'Jelwid',NULL,231.59,95.57,'M',NULL,'2011-08-13 15:49:00',NULL);
INSERT INTO users VALUES(17,'MrRIP',NULL,18553.65,6489.13,NULL,'1982-11-29','2011-08-13 14:04:00',NULL);
INSERT INTO users VALUES(22,'SmileMV',NULL,24210.56,8774.62,'M','1996-04-27','2011-08-13 14:08:00',NULL);
INSERT INTO users VALUES(30,'veon',NULL,10031.61,3709.61,'M',NULL,'2011-08-13 14:27:00',NULL);
INSERT INTO users VALUES(32,'PinkiePie','Pinkamena Diane Pie',1535.4,739.27,'F',NULL,'2011-08-13 14:50:00',NULL);
INSERT INTO users VALUES(38,'Derevo',NULL,84088.27,30056.79,'M','1991-04-11','2011-08-13 15:08:00',NULL);
INSERT INTO users VALUES(40,'DarthPrevedus',NULL,1376.09,444.31,'M','1987-07-30','2011-08-13 15:25:00',NULL);
INSERT INTO users VALUES(311,'Krueger','VladOS',28707.33,1747.51,'M','1993-02-13','2011-09-29 09:08:00','<img src="https://img-fotki.yandex.ru/get/5402/59841979.32e/0_c858a_cddac314_L" width="222" /><br/>');
INSERT INTO users VALUES(396,'H215','Аши 215',48727.6,17253.11,NULL,NULL,'2011-10-09 19:13:00',NULL);
INSERT INTO users VALUES(14224,'andreymal','Андрей Кашлак',38989.83,11668.22,'M','1995-12-07','2013-04-09 23:26:00','Полутабунчанин-полуробот, кодер, коварный взломщег, адекватный парень при мозгах, мастер скриптов и кудесник алгоритмов, паникёр, нытик, зануда, нетортовщик.');
INSERT INTO users VALUES(15404,'am31','Бот',787336.75,288852.19,NULL,'2013-05-27','2014-02-27 20:15:00',NULL);
INSERT INTO users VALUES(67232,'Sweetieck','Свитти Бэлль лучше всех',1659.34,593.79,'M',NULL,'2023-11-08 12:28:00',NULL);


CREATE TABLE blogs(
    id int not null primary key,
    slug text not null,
    name text not null,
    creator_id int not null,
    rating real not null,
    status int not null,
    description mediumtext default null,
    vote_count int not null,
    created_at datetime not null
);

INSERT INTO blogs VALUES(4,'news','Срочно в номер',1,3076.0,0,replace(replace('Новостной блог брони-сообщества. Правила, указанные ниже обязательны для исполнения всеми авторами и комментаторами блога.<br/>\r\n<br/>\r\n<strong>1.</strong> К публикации разрешены новости, касающиеся только вселенной MLP и новости брони-сообщества регионального или глобального масштаба.<br/>\r\n<br/>\r\n<strong>2.</strong> При публикации необходимо указывать ссылку на источник новости.<br/>\r\n<br/>\r\n<strong>3.</strong> Теги должны отображать содержание публикации. При публикации новостей, касающихся:<br/>\r\n<ul><li>конкретной серии необходимо ставить тег «S##E##», где S## — номер сезона, а E## — номер серии. Напр.: S06E12</li><li>конкретного сезона сериала необходимо ставить тег «season #», где # — номер сезона</li><li>фильмов серии Equestria Girls необходимо ставить тег «EG#», где # — номер фильма.</li><li>полнометражного фильма MLP: The Movie необходимо ставить тег «MLP: The Movie»</li><li>официальных комиксов IDW необходимо ставить тег «IDW»</li><li>проводимых конвентов и иных крупных мероприятый необходимо ставить тег «IRL»</li><li>неподтвержденной информации необходимо ставить тег «слухи»</li></ul><strong>4.</strong> Заголовок новости должен содержать указание о содержании поста. При публикации новостей, касающихся:<br/>\r\n<ul><li>серий сериала MLP необходимо ставить перед заголовком префикс [# сезон], где # — номер сезона</li><li>фильмов Equestria Girls необходимо ставить префикс [EG#], где # — номер фильма.</li><li>полнометражного фильма MLP: The Movie необходимо ставить префикс [MLP: The Movie]</li><li>официальных комиксов IDW необходимо ставить префикс [Комиксы IDW]</li><li>неподтвержденной информации необходимо ставить префикс [Слухи]</li></ul><strong>5.</strong> Запрешены:<br/>\r\n<ul><li>публикация материалов с рейтингом выше PG-13</li><li>публикация более чем двух новостей за сутки одним автором. Рекомендуется объединять посты.</li><li>публикация заведомо ложной информации</li><li>графические изображения или видео в количествее более 1 или свыше 600px по горизонтали/вертикали. В противном случае они должны находиться под катом.</li><li>личные оскорбления в комментариях. Излишне агрессивное обсуждение будет пресекаться путем закрытия комментариев при достижении порога в 150 комментариев.</li><li>теги, не соответствующие содержанию публикуемой новости</li><li>любая реклама, за исключениев новостей о проводимых конвентах или иных крупных мероприятиях</li></ul><strong>6.</strong> Изменение постов для соответствия правилам производится администраторами без предварительного уведомления автора.','\r',char(13)),'\n',char(10)),367,'2011-08-11 20:00:00');
INSERT INTO blogs VALUES(407,'night-ponyville','Понивиль После Полуночи',6,3341.99,1,replace(replace('Блог для тех, кто знает значение слова plot. Вход строго по приглашениям. <strong>Приглашения строго по достижению 18 лет.</strong><br/>\r\nПРАВИЛА БЛОГА:<br/>\r\n<u>1. Пост ложится под кат целиком. Всё что под катом раскладывается под спойлер. </u><br/>\r\nПричина: Вкусы разные. Лично я не хочу увидеть футашай даже случайно.<br/>\r\n<u>2. Название поста должно максимально полно и адекватно отображать его содержимое. То же самое касается и тегов. Обязательны теги автора. Если не знаете — «автор неизвестен», и как только откомментивший скажет чье это творение, ставим правильный тег. Теги авторства — на английском.</u><br/>\r\nПричина: Чтобы предотвратить появление кучи публикаций с ничего не значащими именами типа «горячие поньки ХХХ» с Дискорд-знает-чем внутри. И да, легче будет искать любимого автора, при этом мне не нужно будет собирать все посты в огромный мегапотс имени каждого автора и лишать запостившего заслуженных плюсов. Легче будет ориентироваться в тематике. В общем, ради гармонии и порядка. Также добавляйте в скобках автора и то, что именно внутри: комикс\арт\видео\аск-блог и т.д.<br/>\r\n<u>3. Если постите антро, не забывайте тег «АНТРО».</u><br/>\r\nПричина: Я предвзятая скотина и очень не люблю антропоморф и фуррей.<br/>\r\n3.1 Для того, чтобы разделять оригинальный контент и баяны с репостами, добавляйте <u><strong>и</strong> в теги</u> <u><strong>и</strong> в название поста</u> «ОК» <u>русскими буквами</u>. Это поможет быстрее находить оригинальные творения и не открывать то, что вы, при минимальном нахождении в интернете вне Табуна, уже видели.<br/>\r\n3.2 Запрещено постить фоалкон автора Sapsan (спасибо Роскомнадзору)<br/>\r\n<br/>\r\nP.S. GaPAoT самодур и может забанить за нарушение, формально правила не нарушающие.','\r',char(13)),'\n',char(10)),488,'2011-10-08 20:00:00');
INSERT INTO blogs VALUES(4122,'technical','/dev/tabun',1,2084.11,0,replace(replace('<pre>root@everypony:~# cat /dev/tabun &gt; /dev/brain</pre><br/>\r\n<h4>Технический блог Табуна.</h4><em>«Разработка, исправление ошибок, расширение возможностей.»</em><br/>\r\n<br/>\r\n<strong>Правила блога:</strong><br/>\r\n<br/>\r\n<ul><li>00000000. Блог технический.</li><li>00000001. Это значит, что любое проявление флуда, флейма, оффтопика, споров, а также базового незнания мануалов (в т.ч. русского языка), FAQ и правил будет быстро и решительно отправляться в /dev/null, а замеченные — в /dev/moon.</li><li>00000010. Блог предназначен для централизованого сбора багрепортов, рациональных предложений развития технической части, а также как доска объявлений по ней же.</li><li>00000011. Для сбора багрепортов есть специальная тема.</li><li>00000100. Для внесения рациональных предложений есть специальная тема.</li><li>00000101. Блог предназначен для работы только с Табуном. Все остальные технические вопросы перенаправляются в соответствующий раздел Форума. Тема про Табун в техразделе форума остается аварийной — на всякий случай.</li><li>00000110. На вопросы и посты, заданные по технической части вне этого блога, ответов не будет — по понятным причинам.</li><li>00000111. Прежде чем задать вопрос и/или внести предложение — не поленитесь воспользоваться поиском, во избежание 00000001.</li></ul><strong>Новости | <a href="https://tabun.everypony.ru/blog/technical/30775.html" rel="nofollow">Архив</a></strong> <br/>\r\n<a href="https://tabun.everypony.ru/blog/30774.html" rel="nofollow">Изменения в блогах</a><br/>\r\n<a href="https://tabun.everypony.ru/blog/technical/30729.html" rel="nofollow">Интегрированый смайлопак Табуна: пресс-релиз</a><br/>\r\n<a href="https://tabun.everypony.ru/blog/technical/30329.html" rel="nofollow">Техническая чистка графики</a><br/>\r\n<br/>\r\nПредложения по самому блогу — в личку.','\r',char(13)),'\n',char(10)),211,'2012-05-06 20:00:00');
INSERT INTO blogs VALUES(8037,'borderline','На Грани',6,3147.0,2,replace(replace('Слишком откровенно для открытых блогов, но слишком скромно для ППП? Вам сюда!<br/>\r\n<br/>\r\nЭротика, крупы, откровенные позы, прочий не-совсем-гуро и немного-больше-чем-шипинг контент — всё это приветствуется в нашем закрытом, но привечающем любого зрителя блоге. Правила довольно просты:<br/>\r\n<br/>\r\n1. Именовать посты по содержанию.<br/>\r\n2. Класть содержимое под спойлер или кат.<br/>\r\n3. Указывать авторов и источники.<br/>\r\n4. Не путать — сюда постится контент на грани фола, для остального есть либо открытые блоги, либо «Всё о шиппинге» и «ППП».<br/>\r\n5. Для разделения репостов и оригинального контента, в название и теги топика, содержащего оригинальный контент (то есть творчество автора поста), следует добавлять ОК (<u>русскими буквами</u>)<br/>\r\n(0. Админ — самодур, но ленив. Бан нарушителей нетороплив, но неотвратим)<br/>\r\n<br/>\r\n<span><strong>Блог полузакрытый, инвайтов не нужно, жмите «Подписаться на блог» чтобы вступить.</strong></span>','\r',char(13)),'\n',char(10)),378,'2012-09-29 20:00:00');
INSERT INTO blogs VALUES(15738,'apc','Автопресса',14224,1495.29,0,replace(replace('Ежедневно в полночь бот tabun_feed.py с помощью плагина herald.py верстает вестник и публикует сюда.','\r',char(13)),'\n',char(10)),142,'2013-11-24 20:00:00');


CREATE TABLE posts(
    id int not null primary key,
    created_at datetime not null,
    blog_id int default null,
    blog_status int not null,
    author_id int not null,
    title text not null,
    vote_count int not null,
    vote_value int default null,
    body mediumtext not null,
    tags text not null,
    favorites_count int not null
);

INSERT INTO posts VALUES(2,'2011-08-13 13:18:41',NULL,0,5,'Тестирования псто',5,3,replace(replace('Что ж, посмотрим, что из всего этого выйдет.\r\n\r\n(И всё-таки — почему пони в шапке бегут налево?..)','\r',char(13)),'\n',char(10)),'просто так',41);

INSERT INTO posts VALUES(8,'2011-08-13 14:35:52',NULL,0,22,'Instant Derpy!!!',11,16,replace(replace('<a href="http://browse.deviantart.com/?qh=&amp;section=&amp;q=derpy+hooves#/d3lncr2" rel="nofollow">Дерпи такая милашка!!!</a><br/>\r\n<br/>\r\nП.С. Если спросят, то это для теста.<br/>\r\nП.П.С. Нифига это не тест.','\r',char(13)),'\n',char(10)),'Дерпи',0);

-- dice test
INSERT INTO posts VALUES(35481,'2012-09-06 04:04:10',4122,0,7,'##1d100##',104,327,replace(replace('По просьбам RPG-блогов сделаны дайсы, они же — «кубики».<br/>\r\nКак это работает?<br/>\r\nВ посте конструкция вида ##<strong>x</strong>d<strong>y</strong>## (где <strong>x</strong> и <strong>y</strong> — неотрицательные целые числа, <strong>х,y</strong>∈[1;100]) заменяется на нечто вроде:<br/>\r\n<span class="dice"><span class="blue">6d18</span>: <span class="green">[5 + 10 + 4 + 14 + 8 + 4]</span> | <span class="red">[45]</span></span><br/>\r\nСлева — собственно значения <strong>x</strong>d<strong>y</strong>. Справа — <strong>x</strong> раз выпавшие значения <strong>y</strong>-гранника и их сумма.<br/>\r\nНастоящие дайсы — только, и только <strong>цветные</strong>.<br/>\r\nВ режиме редактирования комментариев функция дайсов отключена, FTGJ. Тестируйте, и да пребудет с вами random()!','\r',char(13)),'\n',char(10)),'мелочь,дайсы,доработка,табун,РПГ',9);

-- semi-closed test
INSERT INTO posts VALUES(54657,'2013-02-16 20:17:37',8037,2,17,'O.Z.E. "зубки"',34,NULL,replace(replace('Итак, Все приходят к «кексикам». рано или поздно. Вот и наш Азиатский «друг» решил начать серию картинок.<br/>\r\nПо сути — третья. которую он нарисован с Дианой.<br/>\r\nОбщем — милости просим под кат.<br/>\r\n<a rel="nofollow"></a> <br/>\r\n<span class="spoiler"><span class="spoiler-title" onclick="return true;">Зубки</span><span class="spoiler-body"><img src="http://files.everypony.ru/poniez_archive/2013/02/17/5sICT.jpg"/></span></span><br/>\r\nСурс: <a href="http://www.pixiv.net/member_illust.php?mode=medium&illust_id=33634363" rel="nofollow">www.pixiv.net/member_illust.php?mode=medium&illust_id=33634363</a><br/>\r\nНи на ДА, ни в тамблере ЭТОЙ картинки нет :) Так сказать — ЭКСКЛЮЗИВ!','\r',char(13)),'\n',char(10)),'Пинкиамина Диана Пай,Рейнбо Деш',2);

-- late post
INSERT INTO posts VALUES(213732,'2023-12-31 20:59:59',15738,0,15404,'Автоматический Вестник Табуна №3657 от 31.12.2023',33,122,replace(replace('<img src="//cdn.everypony.ru/storage/01/54/04/2023/12/31/abe8e17f19.jpg" />','\r',char(13)),'\n',char(10)),'Автоматический Вестник Табуна',1);


CREATE TABLE comments(
    id int not null primary key,
    post_id int default null,
    parent_id int default null,
    author_id int not null,
    created_at datetime not null,
    vote_value int not null,
    body mediumtext not null,
    favorites_count int not null
);

INSERT INTO comments VALUES(28,8,NULL,11,'2011-08-13 14:39:55',0,'Теперь у меня 20 новых сообщений!',1);
INSERT INTO comments VALUES(31,8,NULL,14,'2011-08-13 14:45:20',1,'<object width="450" height="260" data="http://www.deviantart.com/download/217760078/instant_derpy__extra__by_ganton3-d3lncr2.swf" type="application/x-shockwave-flash"><param name="wmode" value="opaque"></param><param name="data" value="http://www.deviantart.com/download/217760078/instant_derpy__extra__by_ganton3-d3lncr2.swf"></param><param name="src" value="http://www.deviantart.com/download/217760078/instant_derpy__extra__by_ganton3-d3lncr2.swf"></param></object>',1);
INSERT INTO comments VALUES(32,8,NULL,30,'2011-08-13 14:45:26',0,'<img src="https://lh3.googleusercontent.com/-Fqg_eM3ZUBc/TWxxCYaFZyI/AAAAAAAAB38/k9o3kdd2cCQ/s320/Capture.JPG"/>',1);
INSERT INTO comments VALUES(33,8,31,14,'2011-08-13 14:46:10',0,'↑ мне одному кажется, что позволять так делать — опасно?',1);
INSERT INTO comments VALUES(35,8,31,22,'2011-08-13 14:52:16',0,'Чорд, как ты это вставил?',1);
INSERT INTO comments VALUES(37,8,35,14,'2011-08-13 14:54:50',0,'Великая магия аштиэмэля. Но раскрывать, пожалуй, не буду, так как эта магия весьма тёмная.',1);
INSERT INTO comments VALUES(47,8,37,22,'2011-08-13 15:13:09',-1,'Я ведь серьезно спросил… Все же, какой код то?',1);
INSERT INTO comments VALUES(65,8,32,17,'2011-08-13 15:29:59',0,'Колись как картинку втулить!',1);
INSERT INTO comments VALUES(76,8,65,1,'2011-08-13 15:36:54',0,'Визуальный редактор для комментариев будет добавлен очень скоро.',1);
INSERT INTO comments VALUES(83,8,NULL,17,'2011-08-13 15:43:14',0,replace(replace('<img src="http://e621.net/data/77/af/77af52cff20cbad7a475e5f038af90fe.png/"/><br/>\r\nПроба','\r',char(13)),'\n',char(10)),1);
INSERT INTO comments VALUES(91,8,83,40,'2011-08-13 15:48:44',0,'Не видать…',1);
INSERT INTO comments VALUES(92,8,91,17,'2011-08-13 15:50:42',0,'Я заметил :( Странно. ВЕОН! Колись!',1);
INSERT INTO comments VALUES(94,8,83,14,'2011-08-13 15:53:28',0,'Слеш в конце лишний. Кстати, наверное многие не заметили, но внизу есть кнопочка «предпросмотр».',1);
INSERT INTO comments VALUES(96,8,NULL,17,'2011-08-13 15:57:35',2,replace(replace('Проба 2<br/>\r\n<img src="http://e621.net/data/sample/e4/66/e4667e5dffcb43e2b202d953edb06c50.jpg?1313127164"/>','\r',char(13)),'\n',char(10)),1);
INSERT INTO comments VALUES(102,8,91,40,'2011-08-13 16:01:11',0,'[img]http://cs5653.vkontakte.ru/u61733104/140096519/x_c19322b1.jpg[img]',1);
INSERT INTO comments VALUES(106,8,102,40,'2011-08-13 16:02:37',0,'Тваюжналево…',1);
INSERT INTO comments VALUES(109,8,94,17,'2011-08-13 16:04:12',0,'Спасибо добрый дядко :) Просто я ковычки одни не добавил :(',1);
INSERT INTO comments VALUES(124,8,NULL,40,'2011-08-13 16:14:10',0,'нихрена не пони… Что тут за кодировки? А то я только BB-code знаю… Слоупони я…',1);
INSERT INTO comments VALUES(129,8,96,10,'2011-08-13 16:16:29',0,'Эта Дерпи напомнила мне Кейли из Светлячка.',1);
INSERT INTO comments VALUES(136,8,124,17,'2011-08-13 16:18:45',1,replace(replace('Раскрываю великую тайну:<br/>\r\nimg src=«<a href="https://lh3.googleusercontent.com/-Fqg_eM3ZUBc/TWxxCYaFZyI/AAAAAAAAB38/k9o3kdd2cCQ/s320/Capture.JPG" rel="nofollow">lh3.googleusercontent.com/-Fqg_eM3ZUBc/TWxxCYaFZyI/AAAAAAAAB38/k9o3kdd2cCQ/s320/Capture.JPG</a>»/<br/>\r\nПеред нужно поставить &lt; а после &gt; :) удачных экспериментов.','\r',char(13)),'\n',char(10)),1);
INSERT INTO comments VALUES(137,8,124,38,'2011-08-13 16:19:47',1,'Это ХТМЛ. Немного раньше чем ПХП и ББ появились.',1);
INSERT INTO comments VALUES(172,8,136,40,'2011-08-13 16:51:49',0,'Ясно… Спасиб…',1);
INSERT INTO comments VALUES(174,8,137,40,'2011-08-13 16:53:40',0,'Понятно… ХТМЛ я толком не знаю, буду разбирацо…',1);
INSERT INTO comments VALUES(189,8,106,47,'2011-08-13 17:11:31',0,'<a href="http://tabun.everypony.ru/Jelwid/zaselyaemsya.html" rel="nofollow">tabun.everypony.ru/Jelwid/zaselyaemsya.html</a>',1);

-- semi-closed test
INSERT INTO comments VALUES(3064366,54657,NULL,311,'2013-02-16 21:28:18',3,'Why& <img src="http://img-fotki.yandex.ru/get/4125/59841979.19d/0_8746c_df7b6ef9_-1-XS"/>',0);

-- dice test
INSERT INTO comments VALUES(6269562,35481,NULL,7,'2014-05-12 16:54:58',0,'<span class="dice"><span class="blue">1d100</span>: <span class="green">[39]</span> | <span class="red">[39]</span></span>',0);

-- late comment
INSERT INTO comments VALUES(13745759,2,NULL,396,'2023-09-27 19:17:32',1,'<img src="https://files.everypony.ru/smiles/bc/31/9f68e1.gif" width="195"><br>Ыть ыть ыть!',0);

COMMIT;
