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

# ===== ( Globals ) ============================================================

# Directories
RESOURCE_DIR = os.path.join(os.path.split(__file__)[0], "resources")
HOME_DIR = os.path.expanduser('~')
APP_DIR = os.path.join(HOME_DIR, ".rdfl_exp")
OUT_DIR = os.path.join(APP_DIR, "out")
RUN_DIR = "/var/run/rdfl_exp"
EXP_DIR = str()
CLEANUP = True


# ===== ( Init ) ===============================================================

def init(force=False):
    if not hasattr(init, "done"):
        init.done = False

    if init.done is True and force is True:
        raise RuntimeError("The configuration initialization should be run only"
                           "once. Set \"force=True\" should be set to bypass"
                           "this error")

    __setup_directories()
    __setup_pid()


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
    user = None
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


def __setup_directories():
    """
    Check the availability of the run folder.
    """
    global RUN_DIR
    global APP_DIR
    global OUT_DIR
    global EXP_DIR

    # First we check if the run folder already exists or we create one
    if not os.path.exists(RUN_DIR):
        try:
            os.mkdir(RUN_DIR)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create run direction under {}. ".format(RUN_DIR)
                + "Please verify the script got root permissions"
            )

    # Then check if the APP_DIR exists
    if not os.path.exists(APP_DIR):
        try:
            os.mkdir(APP_DIR)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create application directory at {}. ".format(
                    APP_DIR)
            )

    # Then check if the out folder exists
    if not os.path.exists(OUT_DIR):
        try:
            os.mkdir(OUT_DIR)
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create output directory under {}. ".format(OUT_DIR)
            )

    # Create the folder for the current experiment
    EXP_DIR = join(OUT_DIR, datetime.now().strftime("%Y%m%d_%H%M%S"))
    if not os.path.exists(EXP_DIR):
        try:
            os.mkdir(EXP_DIR)
            os.mkdir(join(EXP_DIR, "datasets"))
        except Exception:
            raise SystemExit(
                Fore.RED + Style.BOLD + "Error" + Style.RESET
                + ": Cannot create experience directory under {}.".format(EXP_DIR)
            )
# End def setup_directories


def __setup_pid():
    """
    Check the presence of a pid file and verify if another experiment isn't
    running.
    """

    if os.path.isfile("{}/pid".format(RUN_DIR)):
        # There is a PID
        with open("{}/pid".format(RUN_DIR), 'r') as pid_file:
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

                os.remove("{}/pid".format(RUN_DIR))

    # If there is no pid we create one for this program
    with open("{}/pid".format(RUN_DIR), 'w') as pid_file:
        pid_file.write(str(os.getpid()))
# End def setup_pid
