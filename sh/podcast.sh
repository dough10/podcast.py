#!/bin/bash

CMD="$HOME/podcast.py/.venv/bin/python3 $HOME/podcast.py/podcast.py"

if [ -n "$1" ]; then
    CMD="$CMD $1"
fi

if [ -n "$2" ]; then
    CMD="$CMD $2"
fi

$CMD
