#!/bin/bash

[ -f ~/podcast.py/.env ] && cp -v ~/podcast.py/.env ~/.podcast.py-env
bash ~/podcast.py/uninstall.sh
cd ~/
curl -O https://raw.githubusercontent.com/dough10/podcast.py/refs/heads/main/install.sh
bash install.sh
rm install.sh
[ -f ~/.podcast.py-env ] && cp -v ~/.podcast.py-env ~/podcast.py/.env