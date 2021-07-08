#!/usr/bin/env python3
# coding: utf-8
import os

APP_NAME = 'RDFL_EXP'
PYTHON_VERSION = '3.9'

# Directories
RESOURCE_DIR = os.path.join(os.path.split(__file__)[0], "resources")
HOME_DIR = os.path.expanduser('~')
APP_DIR = os.path.join(HOME_DIR, ".RDFL_EXP")
OUT_DIR = os.path.join(APP_DIR, "out")
RUN_DIR = "/var/run/RDFL_EXP"
