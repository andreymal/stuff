#!/usr/bin/env bash

set -e

. env.sh

NAME="timelapse_2020-10-10"

for x in `seq 2`; do
  "$PYTHON" -m pixel_battle.img2video_prepare img my/src \
    --begin "$BEGIN" --end "$END" --extra "$EXTRA" --font "$PB_FONT"
done

python -m pixel_battle.img2video --force my/src "my/$NAME.mp4" --list "my/$NAME.txt" \
  --format h264 -p rgb24 -ir 30 \
  --extra "$EXTRA" \
  --begin "$BEGIN" --end "$END"

cp -Rpv "my/$NAME.mp4" "$NAME.mp4"
chmod a+r "$NAME.mp4"
cp -Rpv "my/$NAME.txt" "$NAME.txt"
chmod a+r "$NAME.txt"
