#!/bin/bash

cd ~/podcast.py || exit
git reset --hard
git clean -fd
git pull