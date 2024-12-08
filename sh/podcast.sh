#!/bin/bash

# Define the base command to run the Python script
CMD="$HOME/podcast.py/.venv/bin/python3 ~/podcast.py/podcast.py"

# If $1 is provided, append it to the command
if [ -n "$1" ]; then
    CMD="$CMD $1"
fi

# If $2 is provided, append it to the command
if [ -n "$2" ]; then
    CMD="$CMD $2"
fi

# Execute the command
$CMD
