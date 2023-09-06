#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

# Local dependencies
from fuzzsdn import main
from fuzzsdn.common.utils.terminal import Fore, Style


# ====== (Main Function) ===============================================================================================

if __name__ == '__main__':

    # Check that we have root permissions to run the program
    if os.geteuid() == 0:
        raise SystemExit(Fore.RED + Style.BOLD + "Error" + Style.RESET
                         + ": This program must not be run with root permissions."
                         + " Try again without using \"sudo\".")
    main.main()
