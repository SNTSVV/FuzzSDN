#!/bin/bash
if [ "$EUID" -ne 0 ]
    then echo "Please run as root"
    exit
fi

# Get the directories
ORIGIN=$(pwd -P)
SCRIPT_DIR=$(cd -P -- "$(dirname -- "$0")" && pwd -P)
PROJECT_DIR="$SCRIPT_DIR/.."


# Create configuration folder
if [ ! -d "/etc/packetfuzzer/" ]; then
    mkdir /etc/packetfuzzer
fi

# And copy configuration files there
echo "Creating main configuration"
cp "$PROJECT_DIR/conf/packetfuzzer.conf" "/etc/packetfuzzer/packetfuzzer.conf"
cp "$PROJECT_DIR/conf/packetfuzzer.conf" "/etc/packetfuzzer/packetfuzzer.conf.default"
chmod ugo=r "/etc/packetfuzzer/packetfuzzer.conf.default"

# Create log folder
echo "Creating log folder"
if [ ! -d "/var/log/packetfuzzer" ]; then
    mkdir /var/log/packetfuzzer
    mkdir /var/log/packetfuzzer/logs
    mkdir /var/log/packetfuzzer/pcap
fi

echo Done