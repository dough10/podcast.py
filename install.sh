#!/bin/bash

set -e

package='podcast.py'

version=0.1

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
echo -e "${GREY}${package}${NC}${WHITE} Envoronment Installer v${NC}${GREEN}${version}${NC}";
echo -e ""
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
sudo ln -sfv ~/$package/uninstall.sh /usr/local/bin/${package}_uninstall
sudo ln -sfv ~/$package/sh/reinstall.sh /usr/local/bin/${package}_reinstall
sudo ln -sfv ~/$package/sh/update.sh /usr/local/bin/${package}_update

echo -e "${YELLOW}Adding execute permissions${NC}"
chmod +x -v sh/*.sh
chmod +x -v *.sh
chmod +x -v $package

echo -e "${YELLOW}Install complete. run ${NC}${CYAN}nano ${package}/.env${NC}${YELLOW} to configure environment.${NC}"

echo -e "${YELLOW}add to ${NC}${GREEN}~/.bashrc${NC}${YELLOW}? (y,n)${NC}"
read -r response
if [ "$response" == "y" ] || [ "$response" == "Y" ]; then
  echo -e "${YELLOW}Backing up ${NC}${GREEN}~/.bashrc${NC}${YELLOW} to ~/.bashrc-backup${NC}"
  cp  ~/.bashrc  ~/.bashrc-backup 

  if ! grep -q "~/$package/.venv/bin/python3 ~/$package/$package" ~/.bashrc; then
    echo -e "${YELLOW}Adding ${package} command to ${NC}${GREEN}~/.bashrc${NC}"
    echo -e "~/$package/.venv/bin/python3 ~/$package/$package" >> ~/.bashrc
  else
    echo -e "${YELLOW}Line already exists in .bashrc, skipping addition.${NC}"
  fi
fi