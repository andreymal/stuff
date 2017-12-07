#!/usr/bin/env bash

set -e

./img2video_prepare.py
./img2video_prepare.py
ffmpeg -framerate 24 -i 'my/src/%09d.png' -c:v libx264 -preset veryslow -crf 0 my/timelapse.mp4
rm ./timelapse.mp4
qt-faststart my/timelapse.mp4 ./timelapse.mp4
chmod a+r ./timelapse.mp4
