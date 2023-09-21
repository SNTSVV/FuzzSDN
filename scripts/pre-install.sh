#!/usr/bin/env bash

# fail on error and report it, debug all lines
set -e -o pipefail

# Verify that the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root"
  exit
fi

# Set the working directory as the directory of the script
cd "$(dirname "$0")" || exit 1

# Use some of the directories
[ "$SUDO_USER" ] && USER=$SUDO_USER || USER=$(whoami)

# Get the XDG directories
USR_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
CONFIG_HOME="${XDG_CONFIG_HOME:-"$USR_HOME/.config"}"
CACHE_HOME="${XDG_CACHE_HOME:-"$USR_HOME/.cache"}"
DATA_HOME="${XDG_DATA_HOME:-"$USR_HOME/.local/share"}"
STATE_HOME="${XDG_STATE_HOME:-"$USR_HOME/.local/state"}"
CONFIG_DIR="${CONFIG_HOME}/fuzzsdn"
LIB_DIR="$USR_HOME/.local/lib"

# Update package manager and upgrade most packages
apt-get update --assume-yes

# Install dependencies
read -p "Install prerequisites? [y/n] " yn
case $yn in
[Yy]*)
  echo "Installing prerequisites..."
  apt-get install --assume-yes --quiet openjdk-11-jdk
  apt-get install --assume-yes --quiet maven
  apt-get install --assume-yes --quiet libjpeg-dev python3.8-dev python3.8-venv
  apt-get install --assume-yes --quiet libmysqlclient-dev -y
  apt-get install --assume-yes --quiet mysql-server -y
  apt-get install --assume-yes --quiet  mininet -y
  curl -sSL https://install.python-poetry.org | python3 -
  echo "Done."
  ;;
[Nn]*)
  echo "Skipping dependencies installation..."
  ;;
*)
  echo invalid response
  exit 1
  ;;
esac

# Set up MySQL
read -p "Set up default MySQL database? [y/n] " yn
case $yn in
[Yy]*)
  echo "Setting up MySQL..."
  mysql -e "CREATE DATABASE IF NOT EXISTS fuzzsdn /*\!40100 DEFAULT CHARACTER SET utf8 */;"
  mysql -e "CREATE USER IF NOT EXISTS fuzzsdn@localhost IDENTIFIED BY 'fuzzsdn';"
  mysql -e "GRANT ALL PRIVILEGES ON fuzzsdn.* TO 'fuzzsdn'@'localhost';"
  mysql -e "FLUSH PRIVILEGES;"
  echo "Done."
  ;;
[Nn]*)
  echo "Skipping MySQL setup..."
  ;;
*)
  echo invalid response
  exit 1
  ;;
esac

# Create the app directories if they don't exist yet
echo "Creating directories..."
mkdir -p "$USR_HOME/.local"
mkdir -p "$CACHE_HOME"
mkdir -p "$DATA_HOME"
mkdir -p "$CONFIG_DIR"
mkdir -p "$STATE_HOME"

# Finally, set the permissions to the user
echo "Setting permissions..."
chown -R "$USER":"$USER" "$USR_HOME/.local" "$CONFIG_DIR" "$CACHE_HOME" "$DATA_HOME" "$CONFIG_DIR" "$STATE_HOME"

# Ask user if he wants to configure passwordless user for the current user
read -p "Grant current user ($USER) with passwordless sudo permissions? [y/n] " yn
case $yn in
[Yy]*)
  echo "$USER ALL=(ALL) NOPASSWD: ALL" | (sudo su -c 'EDITOR="tee" visudo -f /etc/sudoers.d/fuzzsdn')
  echo "Passwordless sudo set for user '$USER'. See configuration with 'sudo visudo -f /etc/sudoers.d/fuzzsdn' "
  ;;
[Nn]*) ;;
*)
  echo invalid response
  exit 1
  ;;
esac

# Exit from the script with success (0)
exit 0
