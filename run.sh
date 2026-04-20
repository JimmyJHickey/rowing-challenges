#!/bin/bash

/home/jimmy/miniconda3/envs/rowing_env/bin/python run.py

cd ../jimmyjhickey.com

git add rowing.md img/rowing/
git commit -m "rowing stats updates $(date '+%Y-%m-%d %H:%M:%S')"
git push
