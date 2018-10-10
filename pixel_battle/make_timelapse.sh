#!/bin/sh

set -e

NAME="timelapse_2018-10-10"

./img2video_prepare.py img my/src --extra 2018.json
./img2video_prepare.py img my/src --extra 2018.json

ffmpeg -hide_banner -loglevel error \
    -r 24 -f concat -i my/src/concat.txt \
    -c:v libx264 -preset veryslow -crf 0 \
    -f mp4 -movflags +faststart -y "my/$NAME.mp4"

cp -Rpv "my/$NAME.mp4" "./$NAME.mp4"
chmod a+r "./$NAME.mp4"
