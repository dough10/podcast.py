#!/bin/bash

set -e

rm -rf ~/podcast.py
rm ~/podcast.log
sudo rm -fv /usr/local/bin/podcast.py*
[ -f ~/.bashrc-backup ] && cp -v ~/.bashrc-backup ~/.bashrc && rm ~/.bashrc-backup