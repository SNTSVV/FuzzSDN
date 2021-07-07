#!/usr/bin/env python3
"""A list of variables that allow printing of colors."""

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[95m'
PURPLE = '\033[95m'
CYAN = '\033[96m'

BOLD = '\033[1m'
UNDERLINE = '\033[4m'

RESET = '\033[0m'


def print_bold(string: str):
    col_str = BOLD + '{}' + RESET
    print(col_str.format(string))
