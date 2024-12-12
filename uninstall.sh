#!/bin/bash

set -e

[ -f ~/.bashrc-backup ] && cp -v ~/.bashrc-backup ~/.bashrc && rm ~/.bashrc-backup
rm -rf ~/podcast.py
rm -v ~/podcast.log
sudo rm -fv /usr/local/bin/podcast.py*
crontab -l | grep -v "podcast.py" | crontab -