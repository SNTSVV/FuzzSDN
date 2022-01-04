#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration module for rdfl_exp
"""

import getpass
import os
import pwd
import tempfile
from datetime import datetime
from os.path import join

from rdfl_exp.utils.terminal import Fore, Style

import logging

# ===== ( Globals ) ============================================================

# Directories
USR_HOME    = os.path.expanduser('~')                   # Path to user home directory
RDFL_ROOT   = os.path.join(USR_HOME, ".rdfl_exp")       # Root path of the application
LOG_PATH    = RDFL_ROOT                                 # Path to the log directory
LOG_NAME    = "rdfl_exp.log"
OUT_PATH    = os.path.join(RDFL_ROOT, "out")            # Path to the output directory
RUN_PATH    = "/var/run/rdfl_exp"                       # Path to the run directory
EXP_PATH    = str()                                     # Path to the experiment folder. Defined when running config.init

# Variables
CLEANUP     = True  # Whether or not a cleanup should be performed


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
    global RUN_PATH
    global RDFL_ROOT
    global OUT_PATH
    global EXP_PATH

    # First we check if the run folder already exists or we create one
    if not os.path.exists(RUN_PATH):
        try:
            os.mkdir(RUN_PATH)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create run direction under {}. ".format(RUN_PATH)
                + "Please verify the script got root permissions"
            )

    # Then check if the root folder exists
    if not os.path.exists(RDFL_ROOT):
        try:
            os.mkdir(RDFL_ROOT)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create root application directory at {}. ".format(
                    RDFL_ROOT)
            )

    # Then check if the log folder exists
    if not os.path.exists(LOG_PATH):
        try:
            os.mkdir(LOG_PATH)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create log directory at {}. ".format(LOG_PATH)
            )

    # Then check if the out folder exists
    if not os.path.exists(OUT_PATH):
        try:
            os.mkdir(OUT_PATH)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create output directory under {}. ".format(OUT_PATH)
            )

    # Create the folder for the current experiment
    EXP_PATH = join(OUT_PATH, datetime.now().strftime("%Y%m%d_%H%M%S"))
    if not os.path.exists(EXP_PATH):
        try:
            os.mkdir(EXP_PATH)
            os.mkdir(join(EXP_PATH, "datasets"))
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

    if os.path.isfile("{}/pid".format(RUN_PATH)):
        # There is a PID
        with open("{}/pid".format(RUN_PATH), 'r') as pid_file:
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

                os.remove("{}/pid".format(RUN_PATH))

    # If there is no pid we create one for this program
    with open("{}/pid".format(RUN_PATH), 'w') as pid_file:
        pid_file.write(str(os.getpid()))
# End def +_setup_pid


def _setup_logger():

    # TODO: add a header
    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Add a trace level to logging
    trace_level = logging.DEBUG - 5

    def log_to_trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(trace_level):
            self._log(trace_level, msg, args, **kwargs)

    def log_to_root(msg, *args, **kwargs):
        logging.log(trace_level, msg, *args, **kwargs)

    logging.addLevelName(trace_level, 'TRACE')
    setattr(logging, 'TRACE', trace_level)
    setattr(logging.getLoggerClass(), 'trace', log_to_trace)
    setattr(logging, 'trace', log_to_root)

    # Add the basic configuration
    logging.basicConfig(
        filename=os.path.join(LOG_PATH, LOG_NAME),
        filemode='w',
        format='%(asctime)s,%(msecs)d | %(name)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S',
        level=logging.DEBUG,
    )
# End def _setup_logger
