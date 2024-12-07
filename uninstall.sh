#!/bin/bash

set -e

rm -rf ~/podcast.py
[ -f ~/.bashrc-backup ] && cp -v ~/.bashrc-backup ~/.bashrc && rm ~/.bashrc-backup