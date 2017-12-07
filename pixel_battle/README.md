# pixel_battle

Набор скриптов, который использовался для сохранения состояния доски и сборки
таймлапса [VK Pixel Battle](http://telegra.ph/Polnaya-istoriya-pervoj-pikselnoj-vojny-VKontakte-10-13)
10-13 октября 2017 года.

Готовые таймлапсы:

*  [Полный (12 минут, 110МБ)](https://andreymal.org/files/pixel_battle/timelapse.mp4)
*  [Быстрый (17 секунд, 25МБ)](https://andreymal.org/files/pixel_battle/timelapse_fast.mp4)

Скрипты:

* `pixel_battle.py` — непосредственно сам сборщик. Скачивает картинку
  по адресу `http://pixel.vkforms.ru/data/1.bmp` каждые несколько секунд/минут
  и сохраняет как оптимизированный PNG в указанный каталог.

* `img2video_prepare.py` — собирает скачанные предыдущим скриптом картинки из
  каталога `img`, пририсовывает снизу дату (берёт из имени файла) и сохраняет
  в `my/src`. Попутно сохраняет даты кадров в `my/datetable.txt`.

* `make_timelapse.sh` и `make_fast_timelapse.sh` — с помощью ffmpeg собирают
  кадры из `my/src` в H.264 lossless видео `timelapse.mp4` и
  `timelapse_fast.mp4` соответственно (на самом деле не совсем lossless,
  так как при конвертировании RGB→YUV некоторые цвета портятся без возможности
  точного восстановления RGB-значения, но не критично: таких битых кадров
  меньше процента от их общего числа).

* `last.html` отдаёт самую свежую картинку, сохранённую первым скриптом.
  (Осторожно, лютейший тяп-ляп и jQuery внутри)
