#!/usr/bin/env bash

set -e

./img2video_prepare.py
./img2video_prepare.py
ffmpeg -framerate 30 -i 'my/src/00%?%?%?%?%?%[037%]0.png' -c:v libx264 -preset veryslow -crf 0 my/timelapse_fast.mp4
rm -f ./timelapse_fast.mp4
qt-faststart my/timelapse_fast.mp4 ./timelapse_fast.mp4
chmod a+r ./timelapse_fast.mp4
