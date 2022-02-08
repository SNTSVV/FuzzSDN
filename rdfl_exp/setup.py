#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration module for rdfl_exp
"""

import getpass
import logging
import os
import pwd
import tempfile
from datetime import datetime
from os.path import join
from pathlib import Path

from appdirs import AppDirs

from rdfl_exp.config import DEFAULT_CONFIG as CONFIG
from rdfl_exp.utils.terminal import Fore, Style

# ===== ( Globals ) ============================================================

# Load the application directories
APP_DIRS = AppDirs("rdfl_exp")

# Directories
OUT_DIR   = os.path.join(APP_DIRS.user_data_dir, "out")    # Path to the output directory
LOG_TRACE_DIR = join(APP_DIRS.user_data_dir, 'log_trace', datetime.now().strftime("%Y%m%d_%H%M%S"))
EXP_PATH  = str()                                         # Path to the experiment folder. Defined when running config.init


# ===== ( Init ) ===============================================================

def init(force=False):
    if not hasattr(init, "done"):
        init.done = False

    if init.done is True and force is True:
        raise RuntimeError("The configuration initialization should be run only"
                           "once. Set \"force=True\" should be set to bypass"
                           "this error")

    _setup_dir_structure()
    _setup_pid()
    _setup_logger()
# End def init


# ===== ( Functions ) ==========================================================

def tmp_dir(get_obj=False):
    """
    Returns the path to the experiment temporary directory (or the object) when
    called. The temporary directory is created on the first call

    :param get_obj: if set to true, the tempfile object will be returned
    :return: the tmp directory obj if get_obj is true, else, the path to the
             tmp directory
    """
    if not hasattr(tmp_dir, "tmp_dir"):
        tmp_dir.tmp_dir = tempfile.TemporaryDirectory()

    return tmp_dir.tmp_dir if get_obj is True else tmp_dir.tmp_dir.name
# end def tmp_dir


def get_user():
    """
    Try to find the user who called sudo/pkexec.
    :return: The user called by sudo or None if it cannot be found.
    """

    try:
        return os.getlogin()
    except OSError:
        # failed in some ubuntu installations and in systemd services
        pass

    try:
        user = os.environ['USER']
    except KeyError:
        # possibly a systemd service. no sudo was used
        return getpass.getuser()

    if user == 'root':
        try:
            return os.environ['SUDO_USER']
        except KeyError:
            # no sudo was used
            pass

        try:
            pkexec_uid = int(os.environ['PKEXEC_UID'])
            return pwd.getpwuid(pkexec_uid).pw_name
        except KeyError:
            # no pkexec was used
            pass

    return user
# End def get_user

# ===== ( Private config functions ) ===========================================


def _setup_dir_structure():
    """
    Check the availability of the run folder.
    """
    global OUT_DIR
    global EXP_PATH

    # Check if the user data directory exists
    if not os.path.exists(APP_DIRS.user_data_dir):
        try:
            # Data path
            Path(APP_DIRS.user_data_dir).mkdir(parents=True, exist_ok=True)
            # output directory
            Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create user data directory at \"{}\". ".format(APP_DIRS.user_data_dir)
            )

    # TODO: refactor this whole module
    Path(LOG_TRACE_DIR).mkdir(parents=True, exist_ok=True)

    # Check if the user cache directory exits and if the run directory exists as well
    if not os.path.exists(APP_DIRS.user_cache_dir):
        try:
            # cache directory
            Path(APP_DIRS.user_cache_dir).mkdir(parents=True, exist_ok=True)
            # log directory
            Path(APP_DIRS.user_log_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create directories at \"{}\". ".format(APP_DIRS.user_cache_dir)
                + "Please verify the script got root permissions"
            )

    # Then check if the out folder exists
    if not os.path.exists(OUT_DIR):
        try:
            Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create output directory at \"{}\". ".format(OUT_DIR)
            )

    # Then check if the log folder exists
    if not os.path.exists(APP_DIRS.user_log_dir):
        try:
            Path(APP_DIRS.user_log_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create log directory at \"{}\". ".format(APP_DIRS.user_log_dir)
            )

    # Create the folder for the current experiment
    EXP_PATH = join(OUT_DIR, datetime.now().strftime("%Y%m%d_%H%M%S"))
    if not os.path.exists(EXP_PATH):
        try:
            Path(join(EXP_PATH, "datasets")).mkdir(parents=True, exist_ok=True)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create experience directory under {}.".format(EXP_PATH)
            )
# End def setup_directories


def _setup_pid():
    """
    Check the presence of a pid file and verify if another experiment isn't
    running.
    """

    pid_filepath = os.path.join(APP_DIRS.user_cache_dir, "rdfl_exp.pid")

    if os.path.isfile(pid_filepath):
        # There is a PID
        with open(pid_filepath, 'r') as pid_file:
            pid = int(pid_file.readline().rstrip())

        # If the pid is different, we exit the system and notify the user
        if pid != os.getpid():
            try:
                os.kill(pid, 0)
            except OSError:
                process_exists = False
            else:
                process_exists = True

            if process_exists is True:
                raise SystemExit(Fore.YELLOW + Style.BOLD + "Warning"
                                 + Style.RESET
                                 + ": Another experiment is already running "
                                 + "with pid: {}.\n".format(pid)
                                 + "You can stop it manually with"
                                 + "\"sudo kill {}\"".format(pid))
            else:
                print(Fore.YELLOW + Style.BOLD + "Warning" + Style.RESET
                      + ": Previous pid file wasn't cleaned correctly by "
                      + "process: {}.\n".format(pid)
                      + "Overwriting old pid_file.")

                os.remove(pid_filepath)

    # If there is no pid we create one for this program
    with open(pid_filepath, 'w') as pid_file:
        pid_file.write(str(os.getpid()))
# End def +_setup_pid


def _setup_logger():
    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Write the header into the new log file
    log_file = os.path.join(APP_DIRS.user_log_dir, CONFIG.logging.filename)
    with open(log_file, 'w') as f:
        header = "\n".join([
            "############################################################################################################",
            "App Name   : {}".format("RDFL_EXP v0.2.0"),
            "PID        : {}".format(os.getpid()),
            "Start Date : {}".format(datetime.now()),
            "============================================================================================================\n"
        ])
        f.writelines(header)

    # Add the configuration
    level_d = {
        'TRACE' : logging.TRACE if logging.TRACE is not None else logging.DEBUG,
        'DEBUG' : logging.DEBUG,
        'INFO'  : logging.INFO,
        'WARN'  : logging.WARNING,
        'ERROR' : logging.ERROR
    }
    level = level_d.get(CONFIG.logging.level, logging.INFO)
    logging.basicConfig(
        filename=log_file,
        filemode='a',  # Use append affix to not overwrite the header
        format='%(asctime)s,%(msecs)d | %(name)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S',
        level=level
    )
# End def _setup_logger
