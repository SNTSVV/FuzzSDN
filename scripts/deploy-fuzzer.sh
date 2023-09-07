#!/bin/bash

# fail on error and report it, debug all lines
set -euo pipefail

# ======================================================================================================================
# Variables
# ======================================================================================================================

FRAMEWORK="fuzzsdn"
USER=$(whoami)
USER_HOME="$(getent passwd "$USER" | cut -d: -f6)"
LIB_HOME="${XDG_LIB_HOME:-"$USER_HOME/.local/lib"}"
JAR_LIB_HOME="$LIB_HOME/$FRAMEWORK"
JAR_PATH=""

# ======================================================================================================================
# Main
# ======================================================================================================================

# 1. Verify that the script is not run as root
if [[ $EUID -eq 0 ]]; then
    echo "Please do not run this script as root; don't sudo it"
    exit 1
fi

# 2. Move to the root directory of the project
cd $(cd $(dirname "${BASH_SOURCE[0]}") > /dev/null 2>&1 && pwd)/../

# 3. Find the built JAR
echo "Finding the JAR file for the fuzzer..."
JAR_PATH=$(find dist/ -name "${FRAMEWORK}-fuzzer*.jar" | head -n 1)
if [[ -z "$JAR_PATH" ]]; then
    echo -e "\e[93mCouldn't find the JAR file for the fuzzer.\e[0m"
    echo "Please run 'make fuzzer/build' or 'make build' before running this script."
    exit 1
fi
echo "Found the JAR file at $JAR_PATH"

# 3. Copy the JAR to the bin directory
echo "Copying the JAR file to $JAR_LIB_HOME..."
if [[ ! -d "$JAR_LIB_HOME" ]]; then
    mkdir -p "$JAR_LIB_HOME"
fi
cp "$JAR_PATH" "$JAR_LIB_HOME/$FRAMEWORK-fuzzer.jar"

# 4. Copy the configuration file to the config directory
echo "Creating the configuration file for the application..."
mkdir -p "$USER_HOME/.config/$FRAMEWORK"
if [[ ! -f "$USER_HOME/.config/$FRAMEWORK/fuzzsdn-fuzzer.cfg" ]]; then
    cp "./etc/fuzzsdn-fuzzer.cfg" "$USER_HOME/.config/$FRAMEWORK/fuzzsdn-fuzzer.cfg"
fi

echo "Done."