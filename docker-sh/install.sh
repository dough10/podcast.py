#!/bin/bash

set -e

package='podcast.py'

cd /$package || exit

python3 -m venv .venv

.venv/bin/python3 -m pip install -r requirements.txt

ln -sfv "/podcast.py/docker-sh/podcast.sh" /usr/local/bin/${package}

chmod +x -v ./docker-sh/*.sh
chmod +x -v "./$package"

(crontab -l 2>/dev/null; echo "@reboot $package") | crontab -
(crontab -l 2>/dev/null; echo "0 0 * * * $package") | crontab -

service cron start