#!/bin/bash

current_directory=$(pwd)

parent_directory=$(dirname "$current_directory")

cd $parent_directory
git pull