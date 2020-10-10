#!/usr/bin/env bash

umask 0022

mkdir -p my/src
chmod 700 my

PYTHON="python3"
BEGIN="2020-10-10_12/2020-10-10_12-01-30.png"
END="2020-10-10_14/2020-10-10_14-48-20.png"
EXTRA="2020.json"

# Update for your system
PB_FONT="/usr/share/fonts/TTF/Arial.TTF"
