#!/bin/bash

set -e

package='podcast.py'

version=0.8

BLACK='\033[0;30m'
RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
GREY='\033[0;37m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${ORANGE} _____    ______   _    _   ______   _    _  10${NC}";
echo -e "${ORANGE}| | \ \  / |  | \ | |  | | | | ____ | |  | |   ${NC}";
echo -e "${ORANGE}| | | |  | |  | | | |  | | | |  | | | |--| |   ${NC}";
echo -e "${ORANGE}|_|_/_/  \_|__|_/ \_|__|_| |_|__|_| |_|  |_|   ${NC}";
echo -e "${CYAN}${package}${NC}${WHITE} v${NC}${GREEN}${version}${NC}${WHITE} Envoronment Installer${NC}";
echo ""
echo -e "Legend: ${YELLOW}Status${NC} - ${GREEN}Paths${NC} - ${CYAN}Commands${NC} - ${GREY}Prompt for input${NC} - ${RED}Warnings${NC}"
echo ""
echo -e "${YELLOW}Install Dependencies${NC}"
sudo apt-get update && sudo apt-get install git python3 python3-pip -y
PYTHON_VERSION=$(python3 --version | awk '{print $2}' | cut -d. -f1-2)
PYTHON_VENV_PACKAGE="python${PYTHON_VERSION}-venv"
if ! sudo apt-get install "$PYTHON_VENV_PACKAGE" -y; then
  echo -e "${RED}Warning: ${NC}${GREY}${PYTHON_VENV_PACKAGE}${NC}${RED} installation failed. Attempting to continue...${NC}"
fi
echo -e "${YELLOW}Dependencies Installed${NC}"

echo -e "${YELLOW}Cloning Github repo${NC}"
git clone https://github.com/dough10/$package
echo -e "${YELLOW}Github repo cloned to ${NC}${GREEN}${package}${NC}"

cd $package

echo -e "${YELLOW}Setting virtual environment${NC}"
python3 -m venv .venv
echo -e "${YELLOW}virtual environment ${NC}${GREEN}${package}/.venv${NC}${YELLOW} created${NC}"

echo -e "${YELLOW}Installing requirments.txt to ${NC}${GREEN}${package}/.venv${NC}"
.venv/bin/python3 -m pip install -r requirements.txt
echo -e "${GREEN}${package}/requirments.txt${NC}${YELLOW} installed${NC}"

echo -e "${YELLOW}Installing global commands${NC}"
sudo ln -sfv "$HOME/$package/sh/podcast.sh" "/usr/local/bin/${package}"
sudo ln -sfv "$HOME/$package/uninstall.sh" "/usr/local/bin/${package}_uninstall"
sudo ln -sfv "$HOME/$package/sh/reinstall.sh" "/usr/local/bin/${package}_reinstall"
sudo ln -sfv "$HOME/$package/sh/config.sh" "/usr/local/bin/${package}_config"

echo -e "${YELLOW}Adding execute permissions${NC}"
chmod +x -v ./sh/*.sh
chmod +x -v ./*.sh
chmod +x -v "./$package"

echo -e "${YELLOW}Install complete. run ${NC}${CYAN}${package}_config${NC}${YELLOW} to configure environment.${NC}"

echo -e "${GREY}add to ${NC}${GREEN}~/.bashrc${NC}${GREY}? (y,n) This will run ${NC}${CYAN}${package}${NC}${GREY} when terminal is opened${NC}"
read -r bashrc
if [ "$bashrc" == "y" ] || [ "$bashrc" == "Y" ]; then
  echo -e "${YELLOW}Backing up ${NC}${GREEN}~/.bashrc${NC}${YELLOW} to ${NC}${GREEN}~/.bashrc-backup${NC}"
  cp  ~/.bashrc  ~/.bashrc-backup 

  if ! grep -q "$package" ~/.bashrc; then
    echo -e "${YELLOW}Adding ${NC}${CYAN}${package}${NC}${YELLOW} command to ${NC}${GREEN}~/.bashrc${NC}"
    echo -e "$package" >> ~/.bashrc
  else
    echo -e "${YELLOW}Line already exists in ${NC}${GREEN}~/.bashrc${NC}${YELLOW}, skipping addition.${NC}"
  fi
fi

echo -e "${GREY}Add cronjob? (y,n) will run ${NC}${CYAN}${package}${NC}${GREY} daily at the time you choose${NC}"
read -r cron
if [ "$cron" == "y" ] || [ "$cron" == "Y" ]; then
  while true; do
    echo -e "${GREY}Please enter an hour in 0-23 format:${NC}"
    read -r hour

    if [[ "$hour" -ge 0 && "$hour" -le 23 ]]; then
      break
    else
      echo -e "${RED}Invalid input. Please enter a number between 1 and 24.${NC}"
    fi
  done
  while true; do
    echo -e "${GREY}Please enter minutes (0-59):${NC}"
    read -r minutes

    if [[ "$minutes" -ge 0 && "$minutes" -le 59 ]]; then
      break
    else
      echo -e "${RED}Invalid input. Please enter a number between 0 and 59.${NC}"
    fi
  done
  echo -e "${YELLOW}Cronjob created!${NC}"
  (crontab -l 2>/dev/null; echo "$minutes $hour * * * . $HOME/.bashrc; $package") | crontab -
fi