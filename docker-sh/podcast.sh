#!/bin/bash

CMD="/podcast.py/.venv/bin/python3 /podcast.py/podcast.py"

if [ -n "$1" ]; then
    CMD="$CMD $1"
fi

if [ -n "$2" ]; then
    CMD="$CMD $2"
fi

if [ -n "$3" ]; then
    CMD="$CMD $3"
fi

$CMD