#!/usr/bin/env bash

# fail on error and report it, debug all lines
set -e -o pipefail

# Verify that the script is run as root
if [ "$EUID" -ne 0 ]
  then echo "This script must be run as root"
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
CONFIG_DIR="${CONFIG_HOME}/figsdn"
LIB_DIR="$USR_HOME/.local/lib"

# Update package manager and upgrade most packages
apt-get update --assume-yes

# Install dependencies
apt-get install --assume-yes --quiet openjdk-11-jdk
apt-get install --assume-yes --quiet libjpeg-dev python3.8-dev

# Check mysql installation
apt-get install libmysqlclient-dev -y
apt-get install mysql-server -y
mysql -e "CREATE DATABASE IF NOT EXISTS figsdn /*\!40100 DEFAULT CHARACTER SET utf8 */;"
mysql -e "CREATE USER IF NOT EXISTS figsdn@localhost IDENTIFIED BY 'figsdn';"
mysql -e "GRANT ALL PRIVILEGES ON figsdn.* TO 'figsdn'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# Install Mininet
apt-get install mininet

# Create the app directories if they don't exist yet
mkdir -p "$USR_HOME/.local"
mkdir -p "$CACHE_HOME"
mkdir -p "$DATA_HOME"
mkdir -p "$CONFIG_DIR"
mkdir -p "$STATE_HOME"
cp ../etc/figsdn.cfg "$CONFIG_DIR/figsdn.cfg"  # Copy the configuration file from etc to the root directory

# Finally, set the permissions to the user
chown -R "$USER":"$USER" "$USR_HOME/.local" "$CONFIG_DIR" "$CACHE_HOME" "$DATA_HOME" "$CONFIG_DIR" "$STATE_HOME"

# Ask user if he wants to configure passwordless user for the current user
read -p "Grant current user ($USER) with passwordless sudo permissions ? " yn
case $yn in
	[Yy]* )
	  echo "$USER ALL=(ALL) NOPASSWD: ALL" | (sudo su -c 'EDITOR="tee" visudo -f /etc/sudoers.d/figsdn') ;
    echo "Passwordless sudo set for user '$USER'. See configuration with 'sudo visudo -f /etc/sudoers.d/figsdn' ";;
	[Nn]* ) ;;
	* ) echo invalid response;
		exit 1;;
esac

# Exit from the script with success (0)
exit 0