#!/bin/sh

set -e

NAME="preview"

./img2video_prepare.py img my/src30 -fs 30 --extra 2018.json --concat preview.txt --begin "$1" --end "$2"
./img2video_prepare.py img my/src30 -fs 30 --extra 2018.json --concat preview.txt --begin "$1" --end "$2"

ffmpeg -hide_banner -loglevel error \
    -r 60 -f concat -i my/src30/preview.txt \
    -pix_fmt yuv420p -vf fps=fps=30,scale=960:256 \
    -c:v libx264 -b:v 900k -profile baseline -level 3.0 -preset slow -tune fastdecode -an \
    -f mp4 -movflags +faststart -y "my/$NAME.mp4"

cp -Rpv "my/$NAME.mp4" "./$NAME.mp4"
chmod a+r "./$NAME.mp4"
