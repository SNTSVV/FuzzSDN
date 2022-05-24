# -*- coding: utf-8 -*-
import math
import os
import sys


# ==== ( Define Styles ) ===============================================================================================

class Fore:
    GREY    = '\033[90m'
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    CYAN    = '\033[95m'
    PURPLE  = '\033[95m'
# End class Fore


class Style:
    BOLD            = '\033[1m'
    DISABLE         = '\033[02m'
    UNDERLINE       = '\033[4m'
    REVERSE         = '\033[07m'
    STRIKE_THROUGH  = '\033[09m'
    INVISIBLE       = '\033[08m'
    RESET           = '\033[0m'


# === (banner) =========================================================================================================

banner = r"""{}{}
          ███████╗██╗ ██████╗ ███████╗██████╗ ███╗   ██╗
          ██╔════╝██║██╔════╝ ██╔════╝██╔══██╗████╗  ██║
          █████╗  ██║██║  ███╗███████╗██║  ██║██╔██╗ ██║
          ██╔══╝  ██║██║   ██║╚════██║██║  ██║██║╚██╗██║
          ██║     ██║╚██████╔╝███████║██████╔╝██║ ╚████║
          ╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═════╝ ╚═╝  ╚═══╝{}{}                 
        
        A Failure-Inducing Model generator for SDN systems{}{}        
=================================================================={}""".format(
    Style.BOLD, Fore.YELLOW,     # colors of the logo
    Style.RESET, Fore.PURPLE,  # color of the message
    Style.RESET, Style.BOLD,
    Style.RESET)


# ==== ( Methods ) =====================================================================================================

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return the answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".

    Code taken from @fmark at https://stackoverflow.com/questions/3041986/apt-command-line-interface-like-yes-no-input
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '{}'".format(default))

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")
# End def query_yes_no


def progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', print_end="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        print_end   - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()
# End def progress_bar


def print_list_columns(obj, cols=4, columnwise=True, gap=4):
    """
    Print the given list in evenly-spaced columns.
    Adapted from @ozagon's answer at https://stackoverflow.com/questions/1524126/how-to-print-a-list-more-nicely

    :param obj: The list to be printed.
    :type obj: list
    :param cols: The number of columns in which the list should be printed.
    :type cols: int
    :param columnwise: If True, the items in the list will be printed column-wise.
                       If False the items in the list will be printed row-wise.
    :type columnwise: bool (default=True)
    :param gap: The number of spaces that should separate the longest column
                item/s from the next column. This is the effective spacing
                between columns based on the maximum len() of the list items.
    :type gap: int
    """

    s_obj = [str(item) for item in obj]
    if cols > len(s_obj):
        cols = len(s_obj)
    max_len = max([len(item) for item in s_obj])
    if columnwise:
        cols = int(math.ceil(float(len(s_obj)) / float(cols)))
    plist = [s_obj[i: i + cols] for i in range(0, len(s_obj), cols)]
    if columnwise:
        if not len(plist[-1]) == cols:
            plist[-1].extend([''] * (len(s_obj) - len(plist[-1])))
        plist = zip(*plist)
    printer = '\n'.join([
        ''.join([c.ljust(max_len + gap) for c in p])
        for p in plist])

    print(printer)
# End def print_list_columns

