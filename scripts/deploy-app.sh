#!/bin/bash

# fail on error and report it, debug all lines
set -euo pipefail

# ======================================================================================================================
# Variables
# ======================================================================================================================

MIN_PYTHON_VERSION="3.8"
FRAMEWORK="fuzzsdn"
USER=$(whoami)
USER_HOME="$(getent passwd "$USER" | cut -d: -f6)"
DATA_HOME="${XDG_DATA_HOME:-"$USER_HOME/.local/share"}"
WHEEL_PATH=""
VENV_NAME="fuzzsdn-venv"
VENV_DIR="$DATA_HOME/virtualenv/$VENV_NAME"

# ======================================================================================================================
# Main
# ======================================================================================================================

venv_exists=false

# 1. Verify that the script is not run as root
if [[ $EUID -eq 0 ]]; then
    echo "Please do not run this script as root; don't sudo it"
    exit 1
fi

# 2. Verify that the python version is above 3.9
python_version=$(python3 -c "import sys; print(\"{}.{}\".format(*sys.version_info[:2]))")
python_major=$(echo "$python_version" | cut -d"." -f1)
python_minor=$(echo "$python_version" | cut -d"." -f2)
required_major=$(echo "$MIN_PYTHON_VERSION" | cut -d"." -f1)
required_minor=$(echo "$MIN_PYTHON_VERSION" | cut -d"." -f2)

if [[ $python_major -lt required_major || ($python_major -eq required_major && $python_minor -lt required_minor) ]]; then
    echo -e "\e[93mCurrent python3 version is $python_version, but the minimum required version is $MIN_PYTHON_VERSION\e[0m"
    echo "Please make sure python>=$MIN_PYTHON_VERSION is installed before proceeding."
    exit 1
fi

# 3. Move to the root directory of the project
cd $(cd $(dirname "${BASH_SOURCE[0]}") > /dev/null 2>&1 && pwd)/../

# 4. Check if the wheel exists
echo "Finding the wheel file for the application..."
WHEEL_PATH=$(find dist/ -name "${FRAMEWORK}-*.whl" | head -n 1)
if [[ -z "$WHEEL_PATH" ]]; then
    echo "Couldn't find the wheel file. Please run "
    exit 1
fi
echo "Found the wheel file at $WHEEL_PATH"

# 5. Check if the virtual environment exists, and if it does, delete it
echo "Setting up the virtual environment for the application..."
if [[ -d "$VENV_DIR" ]]; then
    echo "Virtual environment already exists at $VENV_DIR."
    venv_exists=true
fi

# 5. Create the virtual environment
mkdir -p "$VENV_DIR"
python3 -m venv "$VENV_DIR"
source "${VENV_DIR}/bin/activate"

pip install --upgrade pip
pip install setuptools_rust

# 6. Install the wheel in the virtual environment
echo "Installing the application wheel in the virtual environment (at $VENV_DIR)..."
if [[ "$venv_exists" = true ]]; then
    python3 -m pip install --force-reinstall "$WHEEL_PATH"
else
  python3 -m pip install "$WHEEL_PATH"
fi

# 7. Copy the executable to the bin directory
echo "Creating the executable for the application..."
cp "./scripts/$FRAMEWORK" "$USER_HOME/.local/bin/$FRAMEWORK"
chmod +x "$USER_HOME/.local/bin/$FRAMEWORK"

# 8. Copy the configuration file to the config directory
echo "Creating the configuration file for the application..."
mkdir -p "$USER_HOME/.config/$FRAMEWORK"
if [[ ! -f "$USER_HOME/.config/$FRAMEWORK/fuzzsdn.cfg" ]]; then
    cp "./etc/fuzzsdn.cfg" "$USER_HOME/.config/$FRAMEWORK/fuzzsdn.cfg"
fi

echo "Done."