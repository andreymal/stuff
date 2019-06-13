#!/bin/sh

set -e
umask 0022

PYTHON="python3"
NAME="timelapse_2018-10-10"
BEGIN=""
END="2018-10-13_00/2018-10-13_00-10-00.png"
EXTRA="2018.json"

mkdir -p my/src
chmod 700 my

for x in `seq 2`; do
  "$PYTHON" -m pixel_battle img2video_prepare img my/src \
    --begin "$BEGIN" --end "$END"
done

python -m pixel_battle img2video --force my/src "my/$NAME.mp4" --list "my/$NAME.txt" \
  --format h264 -p rgb24 -ir 24 \
  --extra "$EXTRA" \
  --begin "$BEGIN" --end "$END"

cp -Rpv "my/$NAME.mp4" "$NAME.mp4"
chmod a+r "$NAME.mp4"
cp -Rpv "my/$NAME.txt" "$NAME.txt"
chmod a+r "$NAME.txt"
