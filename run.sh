#!/bin/bash

/home/pi/.pyenv/shims/python3 /home/pi/git/rowing-challenges/run.py
cd /home/pi/git/jimmyjhickey.com

git add rowing.md img/rowing/
git commit -m "rowing stats updates $(date '+%Y-%m-%d %H:%M:%S')"
git push
