#!/bin/sh

set -e
umask 0022

PYTHON="python3"
NAME="preview"
EXTRA="2018.json"

mkdir -p my/src
chmod 700 my

for x in `seq 2`; do
  "$PYTHON" -m pixel_battle img2video_prepare img my/src \
    --begin "$1" --end "$2"
done

python -m pixel_battle img2video --force my/src "my/$NAME.mp4" \
  --format h264-baseline -p yuv420p -crf 21 -ir 60 -or 30 \
  --extra "$EXTRA" --scale 960:-1 \
  --begin "$1" --end "$2"

cp -Rpv "my/$NAME.mp4" "$NAME.mp4"
chmod a+r "$NAME.mp4"
