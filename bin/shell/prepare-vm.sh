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

[ "$SUDO_USER" ] && USER=$SUDO_USER || USER=$(whoami)
CONFIG_DIR="$(getent passwd "$SUDO_USER" | cut -d: -f6)/.config/rdfl_exp"

# Update package manager and upgrade most packages
apt-get update --assume-yes

# Install dependencies
apt-get install --assume-yes --quiet openjdk-11-jdk
apt-get install --assume-yes --quiet libjpeg-dev python3.8-dev

## ask user to add environment variable for JAVA_HOME
if [[ -z "$JAVA_HOME" ]]; then
    while true; do
    read -rp "Do you wish to add JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 to /etc/environment ? " yn
    case $yn in
        [Yy]* ) echo "JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64" >> /etc/environment; source /etc/environment; break;;
        [Nn]* ) echo "Please add environment variable: JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 to .bashrc" 1>&2;;
        * ) echo "Please answer yes or no.";;
    esac
done
    echo "Please add environment variable: JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 to .bashrc or /etc/environment" 1>&2
fi

# Check mysql installation
apt-get install libmysqlclient-dev -y
apt-get install mysql-server -y
mysql -e "CREATE DATABASE IF NOT EXISTS rdfl_exp /*\!40100 DEFAULT CHARACTER SET utf8 */;"
mysql -e "CREATE USER IF NOT EXISTS rdfl_exp@localhost IDENTIFIED BY 'rdfl_exp';"
mysql -e "GRANT ALL PRIVILEGES ON rdfl_exp.* TO 'rdfl_exp'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# Create the main directory if it doesn't exist yet
mkdir -p "$CONFIG_DIR"
cp ../../etc/rdfl_exp.cfg "$CONFIG_DIR/rdfl_exp-app.cfg"  # Copy the configuration file from etc to the root directory

# Finally, set the permissions to the user
chown -R "$USER":"$USER" "$CONFIG_DIR"


echo ""
echo "RDFL_EXP configuration complete."
echo ""

# Exit from the script with success (0)
exit 0



# Optionally install in virtual env
function setup_venv {
    # $1 is the path to python implementation, $2 is the venv-name
    echo "Installing virtual env for FIG-SDN..."
    pushd $DIR
    set +o nounset

    if [ -z "$2" ]
    then
        venv_name="venv-fig-sdn"
    else
        venv_name=$2
    fi
    pip install virtualenv

    # Setup virtual env
    if [ -z "$1" ]; then
        echo "No python implementation specified for virtual env, using default."
        virtualenv $venv_name
    else
        python_impl=$1
        echo "Using $python_impl for python in virtual env."
        virtualenv -p $python_impl $venv_name
    fi
    python_reqs $venv_name/bin/pip
    set -o nounset
    popd
}


function xdg_base_dirs {

  # https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html

  # Ensure base distro defaults xdg path are set if nothing filed up some defaults yet.
  export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-"$HOME/.config"}"
  export XDG_CACHE_HOME="${XDG_CACHE_HOME:-"$HOME/.cache"}"
  export XDG_DATA_HOME="${XDG_DATA_HOME:-"$HOME/.local/share"}"
  export XDG_STATE_HOME="${XDG_STATE_HOME:-"$HOME/.local/state"}"
  export XDG_DATA_DIRS="${XDG_DATA_DIRS:-'/usr/local/share/:/usr/share/'}"
  export XDG_CONFIG_DIRS="${XDG_CONFIG_DIRS:-'/etc/xdg'}"

  # $XDG_RUNTIME_DIR should be set by the system. Its access mode MUST be 0700
}