#!/bin/bash

set -e

rm -rf ~/podcast.py
rm ~/podcast.log
[ -f ~/.bashrc-backup ] && cp -v ~/.bashrc-backup ~/.bashrc && rm ~/.bashrc-backup