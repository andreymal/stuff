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
INSERT INTO users VALUES(38,'Derevo',NULL,84088.27,30056.79,'M','1991-04-11','2011-08-13 15:08:00',NULL);
INSERT INTO users VALUES(40,'DarthPrevedus',NULL,1376.09,444.31,'M','1987-07-30','2011-08-13 15:25:00',NULL);
INSERT INTO users VALUES(10,'FrownyFrog',NULL,2.12,26.60,'M','1993-07-04','2011-08-13 13:49:00',NULL);
INSERT INTO users VALUES(11,'McGyver',NULL,304.62,174.71,'M','1992-04-13','2011-08-13 13:50:00',NULL);
INSERT INTO users VALUES(14,'Nekit1234007',NULL,7501.92,2765.98,'M',NULL,'2011-08-13 13:56:00',NULL);
INSERT INTO users VALUES(47,'Jelwid',NULL,231.59,95.57,'M',NULL,'2011-08-13 15:49:00',NULL);
INSERT INTO users VALUES(17,'MrRIP',NULL,18553.65,6489.13,NULL,'1982-11-29','2011-08-13 14:04:00',NULL);
INSERT INTO users VALUES(22,'SmileMV',NULL,24210.56,8774.62,'M','1996-04-27','2011-08-13 14:08:00',NULL);
INSERT INTO users VALUES(30,'veon',NULL,10031.61,3709.61,'M',NULL,'2011-08-13 14:27:00',NULL);


CREATE TABLE blogs(
    id int not null primary key,
    slug text not null,
    name text not null,
    creator_id int not null,
    rating real not null,
    status int not null,
    description mediumtext default null,
    vote_count int not null,
    created_at datetime not null,
    deleted int not null default 0
);

INSERT INTO blogs VALUES(4,'news','Срочно в номер',1,3076.0,0,replace(replace('Новостной блог брони-сообщества. Правила, указанные ниже обязательны для исполнения всеми авторами и комментаторами блога.<br/>\r\n<br/>\r\n<strong>1.</strong> К публикации разрешены новости, касающиеся только вселенной MLP и новости брони-сообщества регионального или глобального масштаба.<br/>\r\n<br/>\r\n<strong>2.</strong> При публикации необходимо указывать ссылку на источник новости.<br/>\r\n<br/>\r\n<strong>3.</strong> Теги должны отображать содержание публикации. При публикации новостей, касающихся:<br/>\r\n<ul><li>конкретной серии необходимо ставить тег «S##E##», где S## — номер сезона, а E## — номер серии. Напр.: S06E12</li><li>конкретного сезона сериала необходимо ставить тег «season #», где # — номер сезона</li><li>фильмов серии Equestria Girls необходимо ставить тег «EG#», где # — номер фильма.</li><li>полнометражного фильма MLP: The Movie необходимо ставить тег «MLP: The Movie»</li><li>официальных комиксов IDW необходимо ставить тег «IDW»</li><li>проводимых конвентов и иных крупных мероприятый необходимо ставить тег «IRL»</li><li>неподтвержденной информации необходимо ставить тег «слухи»</li></ul><strong>4.</strong> Заголовок новости должен содержать указание о содержании поста. При публикации новостей, касающихся:<br/>\r\n<ul><li>серий сериала MLP необходимо ставить перед заголовком префикс [# сезон], где # — номер сезона</li><li>фильмов Equestria Girls необходимо ставить префикс [EG#], где # — номер фильма.</li><li>полнометражного фильма MLP: The Movie необходимо ставить префикс [MLP: The Movie]</li><li>официальных комиксов IDW необходимо ставить префикс [Комиксы IDW]</li><li>неподтвержденной информации необходимо ставить префикс [Слухи]</li></ul><strong>5.</strong> Запрешены:<br/>\r\n<ul><li>публикация материалов с рейтингом выше PG-13</li><li>публикация более чем двух новостей за сутки одним автором. Рекомендуется объединять посты.</li><li>публикация заведомо ложной информации</li><li>графические изображения или видео в количествее более 1 или свыше 600px по горизонтали/вертикали. В противном случае они должны находиться под катом.</li><li>личные оскорбления в комментариях. Излишне агрессивное обсуждение будет пресекаться путем закрытия комментариев при достижении порога в 150 комментариев.</li><li>теги, не соответствующие содержанию публикуемой новости</li><li>любая реклама, за исключениев новостей о проводимых конвентах или иных крупных мероприятиях</li></ul><strong>6.</strong> Изменение постов для соответствия правилам производится администраторами без предварительного уведомления автора.','\r',char(13)),'\n',char(10)),367,'2011-08-11 20:00:00',0);
INSERT INTO blogs VALUES(407,'night-ponyville','Понивиль После Полуночи',6,3341.99,1,replace(replace('Блог для тех, кто знает значение слова plot. Вход строго по приглашениям. <strong>Приглашения строго по достижению 18 лет.</strong><br/>\r\nПРАВИЛА БЛОГА:<br/>\r\n<u>1. Пост ложится под кат целиком. Всё что под катом раскладывается под спойлер. </u><br/>\r\nПричина: Вкусы разные. Лично я не хочу увидеть футашай даже случайно.<br/>\r\n<u>2. Название поста должно максимально полно и адекватно отображать его содержимое. То же самое касается и тегов. Обязательны теги автора. Если не знаете — «автор неизвестен», и как только откомментивший скажет чье это творение, ставим правильный тег. Теги авторства — на английском.</u><br/>\r\nПричина: Чтобы предотвратить появление кучи публикаций с ничего не значащими именами типа «горячие поньки ХХХ» с Дискорд-знает-чем внутри. И да, легче будет искать любимого автора, при этом мне не нужно будет собирать все посты в огромный мегапотс имени каждого автора и лишать запостившего заслуженных плюсов. Легче будет ориентироваться в тематике. В общем, ради гармонии и порядка. Также добавляйте в скобках автора и то, что именно внутри: комикс\арт\видео\аск-блог и т.д.<br/>\r\n<u>3. Если постите антро, не забывайте тег «АНТРО».</u><br/>\r\nПричина: Я предвзятая скотина и очень не люблю антропоморф и фуррей.<br/>\r\n3.1 Для того, чтобы разделять оригинальный контент и баяны с репостами, добавляйте <u><strong>и</strong> в теги</u> <u><strong>и</strong> в название поста</u> «ОК» <u>русскими буквами</u>. Это поможет быстрее находить оригинальные творения и не открывать то, что вы, при минимальном нахождении в интернете вне Табуна, уже видели.<br/>\r\n3.2 Запрещено постить фоалкон автора Sapsan (спасибо Роскомнадзору)<br/>\r\n<br/>\r\nP.S. GaPAoT самодур и может забанить за нарушение, формально правила не нарушающие.','\r',char(13)),'\n',char(10)),488,'2011-10-08 20:00:00',0);
INSERT INTO blogs VALUES(8037,'borderline','На Грани',6,3147.0,2,replace(replace('Слишком откровенно для открытых блогов, но слишком скромно для ППП? Вам сюда!<br/>\r\n<br/>\r\nЭротика, крупы, откровенные позы, прочий не-совсем-гуро и немного-больше-чем-шипинг контент — всё это приветствуется в нашем закрытом, но привечающем любого зрителя блоге. Правила довольно просты:<br/>\r\n<br/>\r\n1. Именовать посты по содержанию.<br/>\r\n2. Класть содержимое под спойлер или кат.<br/>\r\n3. Указывать авторов и источники.<br/>\r\n4. Не путать — сюда постится контент на грани фола, для остального есть либо открытые блоги, либо «Всё о шиппинге» и «ППП».<br/>\r\n5. Для разделения репостов и оригинального контента, в название и теги топика, содержащего оригинальный контент (то есть творчество автора поста), следует добавлять ОК (<u>русскими буквами</u>)<br/>\r\n(0. Админ — самодур, но ленив. Бан нарушителей нетороплив, но неотвратим)<br/>\r\n<br/>\r\n<span><strong>Блог полузакрытый, инвайтов не нужно, жмите «Подписаться на блог» чтобы вступить.</strong></span>','\r',char(13)),'\n',char(10)),378,'2012-09-29 20:00:00',0);


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
    favorites_count int not null,
    deleted int not null default 0,
    draft int not null default 0
);

INSERT INTO posts VALUES(8,'2011-08-13 14:35:52',NULL,0,22,'Instant Derpy!!!',11,16,replace(replace('<a href="http://browse.deviantart.com/?qh=&amp;section=&amp;q=derpy+hooves#/d3lncr2" rel="nofollow">Дерпи такая милашка!!!</a><br/>\r\n<br/>\r\nП.С. Если спросят, то это для теста.<br/>\r\nП.П.С. Нифига это не тест. ','\r',char(13)),'\n',char(10)),0,0,0);


CREATE TABLE comments(
    id int not null primary key,
    post_id int default null,
    parent_id int default null,
    author_id int not null,
    created_at datetime not null,
    vote_value int not null,
    body mediumtext not null,
    deleted int not null default 0,
    favorites_count int not null
);

INSERT INTO comments VALUES(28,8,NULL,11,'2011-08-13 14:39:55',0,'Теперь у меня 20 новых сообщений!',0,1);
INSERT INTO comments VALUES(31,8,NULL,14,'2011-08-13 14:45:20',1,'<object width="450" height="260" data="http://www.deviantart.com/download/217760078/instant_derpy__extra__by_ganton3-d3lncr2.swf" type="application/x-shockwave-flash"><param name="wmode" value="opaque"></param><param name="data" value="http://www.deviantart.com/download/217760078/instant_derpy__extra__by_ganton3-d3lncr2.swf"></param><param name="src" value="http://www.deviantart.com/download/217760078/instant_derpy__extra__by_ganton3-d3lncr2.swf"></param></object>',0,1);
INSERT INTO comments VALUES(32,8,NULL,30,'2011-08-13 14:45:26',0,'<img src="https://lh3.googleusercontent.com/-Fqg_eM3ZUBc/TWxxCYaFZyI/AAAAAAAAB38/k9o3kdd2cCQ/s320/Capture.JPG"/>',0,1);
INSERT INTO comments VALUES(33,8,31,14,'2011-08-13 14:46:10',0,'↑ мне одному кажется, что позволять так делать — опасно?',0,1);
INSERT INTO comments VALUES(35,8,31,22,'2011-08-13 14:52:16',0,'Чорд, как ты это вставил?',0,1);
INSERT INTO comments VALUES(37,8,35,14,'2011-08-13 14:54:50',0,'Великая магия аштиэмэля. Но раскрывать, пожалуй, не буду, так как эта магия весьма тёмная.',0,1);
INSERT INTO comments VALUES(47,8,37,22,'2011-08-13 15:13:09',-1,'Я ведь серьезно спросил… Все же, какой код то?',0,1);
INSERT INTO comments VALUES(65,8,32,17,'2011-08-13 15:29:59',0,'Колись как картинку втулить!',0,1);
INSERT INTO comments VALUES(76,8,65,1,'2011-08-13 15:36:54',0,'Визуальный редактор для комментариев будет добавлен очень скоро.',0,1);
INSERT INTO comments VALUES(83,8,NULL,17,'2011-08-13 15:43:14',0,replace(replace('<img src="http://e621.net/data/77/af/77af52cff20cbad7a475e5f038af90fe.png/"/><br/>\r\nПроба','\r',char(13)),'\n',char(10)),0,1);
INSERT INTO comments VALUES(91,8,83,40,'2011-08-13 15:48:44',0,'Не видать…',0,1);
INSERT INTO comments VALUES(92,8,91,17,'2011-08-13 15:50:42',0,'Я заметил :( Странно. ВЕОН! Колись!',0,1);
INSERT INTO comments VALUES(94,8,83,14,'2011-08-13 15:53:28',0,'Слеш в конце лишний. Кстати, наверное многие не заметили, но внизу есть кнопочка «предпросмотр».',0,1);
INSERT INTO comments VALUES(96,8,NULL,17,'2011-08-13 15:57:35',2,replace(replace('Проба 2<br/>\r\n<img src="http://e621.net/data/sample/e4/66/e4667e5dffcb43e2b202d953edb06c50.jpg?1313127164"/>','\r',char(13)),'\n',char(10)),0,1);
INSERT INTO comments VALUES(102,8,91,40,'2011-08-13 16:01:11',0,'[img]http://cs5653.vkontakte.ru/u61733104/140096519/x_c19322b1.jpg[img]',0,1);
INSERT INTO comments VALUES(106,8,102,40,'2011-08-13 16:02:37',0,'Тваюжналево…',0,1);
INSERT INTO comments VALUES(109,8,94,17,'2011-08-13 16:04:12',0,'Спасибо добрый дядко :) Просто я ковычки одни не добавил :(',0,1);
INSERT INTO comments VALUES(124,8,NULL,40,'2011-08-13 16:14:10',0,'нихрена не пони… Что тут за кодировки? А то я только BB-code знаю… Слоупони я…',0,1);
INSERT INTO comments VALUES(129,8,96,10,'2011-08-13 16:16:29',0,'Эта Дерпи напомнила мне Кейли из Светлячка.',0,1);
INSERT INTO comments VALUES(136,8,124,17,'2011-08-13 16:18:45',1,replace(replace('Раскрываю великую тайну:<br/>\r\nimg src=«<a href="https://lh3.googleusercontent.com/-Fqg_eM3ZUBc/TWxxCYaFZyI/AAAAAAAAB38/k9o3kdd2cCQ/s320/Capture.JPG" rel="nofollow">lh3.googleusercontent.com/-Fqg_eM3ZUBc/TWxxCYaFZyI/AAAAAAAAB38/k9o3kdd2cCQ/s320/Capture.JPG</a>»/<br/>\r\nПеред нужно поставить &lt; а после &gt; :) удачных экспериментов.','\r',char(13)),'\n',char(10)),0,1);
INSERT INTO comments VALUES(137,8,124,38,'2011-08-13 16:19:47',1,'Это ХТМЛ. Немного раньше чем ПХП и ББ появились.',0,1);
INSERT INTO comments VALUES(172,8,136,40,'2011-08-13 16:51:49',0,'Ясно… Спасиб…',0,1);
INSERT INTO comments VALUES(174,8,137,40,'2011-08-13 16:53:40',0,'Понятно… ХТМЛ я толком не знаю, буду разбирацо…',0,1);
INSERT INTO comments VALUES(189,8,106,47,'2011-08-13 17:11:31',0,'<a href="http://tabun.everypony.ru/Jelwid/zaselyaemsya.html" rel="nofollow">tabun.everypony.ru/Jelwid/zaselyaemsya.html</a>',0,1);


COMMIT;
