#!/usr/bin/env bash

set -e

. env.sh

NAME="preview"
BEGIN="$1"
END="$2"

for x in `seq 2`; do
  "$PYTHON" -m pixel_battle.img2video_prepare img my/src \
    --begin "$BEGIN" --end "$END" --extra "$EXTRA" --font "$PB_FONT"
done

python -m pixel_battle.img2video --force my/src "my/$NAME.mp4" \
  --format h264-baseline -p yuv420p -crf 21 -ir 60 -or 30 \
  --extra "$EXTRA" --scale 960:-1 \
  --begin "$BEGIN" --end "$END"

cp -Rpv "my/$NAME.mp4" "$NAME.mp4"
chmod a+r "$NAME.mp4"
