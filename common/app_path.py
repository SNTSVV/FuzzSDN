# -*- coding: utf-8 -*-
"""
Module that determine the application paths
"""
import os
import pwd
import sys
import tempfile
from pathlib import Path
from typing import Optional

from appdirs import AppDirs

# ===== ( Module Globals definition ) ==================================================================================

__FRAMEWORK_NAME__ = "rdfl_exp"

_EXP_REF : Optional[str] = None
_APP_DIR = AppDirs(__FRAMEWORK_NAME__)


_DEFAULT_XDG_STATE_HOME = ""


# ===== ( System definition ) ==========================================================================================

_SYSTEM = ''
if sys.platform.startswith('java'):
    import platform
    os_name = platform.java_ver()[3][0]
    if os_name.startswith('Windows'): # "Windows XP", "Windows 7", etc.
        _SYSTEM = 'win32'
    elif os_name.startswith('Mac'): # "Mac OS X", etc.
        _SYSTEM = 'darwin'
    else: # "Linux", "SunOS", "FreeBSD", etc.
        # Setting this to "linux2" is not ideal, but only Windows or Mac
        # are actually checked for and the rest of the module expects
        # *sys.platform* style strings.
        _SYSTEM = 'linux2'
else:
    _SYSTEM = sys.platform


# ====== () ===

def set_experiment_reference(exp : Optional[str] = None):
    """
    Set a reference for the current experiment, this impact the paths of the application

    :param exp:
    :return:
    """
    global _EXP_REF
    _EXP_REF = exp
# End def set_exp_name


# ===== (Base dirs) ====================================================================================================

def run_dir():
    """
    Returns the path to the folder XDG_RUNTIME_DIR.
    Also makes sure it is created beforehand

    :return:
    """
    uid = pwd.getpwuid(os.getuid()).pw_uid
    if _SYSTEM == 'win32':
        # There is no defined XDG_RUNTIME_DIR on Windows accessible for the user, therefore we return a path in the
        # temporary folder
        path = os.path.join('%TEMP%', "{}-{}".format(__FRAMEWORK_NAME__, uid))

    elif _SYSTEM == 'darwin':
        # There is no defined XDG_RUNTIME_DIR on OSX accessible for the user, therefore we return a path in /tmp/
        path = os.path.join("/tmp/", "{}-{}".format(__FRAMEWORK_NAME__, uid))

    else:  # Linux, etc

        if 'XDG_RUNTIME_DIR' in os.environ:
            path = os.path.join(os.getenv('XDG_RUNTIME_DIR'), __FRAMEWORK_NAME__)
        else:
            path = os.path.join("/tmp/", "{}-{}".format(__FRAMEWORK_NAME__, uid))

    if not os.path.exists(path):
        Path(path).mkdir(mode=0o700, parents=True, exist_ok=True)

    return path


def config_dir():

    path = os.path.join(_APP_DIR.user_config_dir)
    if not os.path.exists(path):
        Path(path).mkdir(exist_ok=True, parents=True)
    return path
# End def _config_dir


def data_dir():
    path = os.path.join(_APP_DIR.user_data_dir)
    if not os.path.exists(path):
        Path(path).mkdir(exist_ok=True, parents=True)
    return path


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


def exp_dir(sub: Optional[str] = None) -> Optional[str]:
    """
    Give access to the current
    :param sub:
    :return:
    """
    if _EXP_REF not in (None, ''):

        root = os.path.join(data_dir(), 'experiments', _EXP_REF)

        if sub in (None, '', 'root'):
            return root
        elif sub.lower() in ('data', 'models', 'logs'):
            path = os.path.join(root, sub)
            if not os.path.exists(path):
                Path(path).mkdir(exist_ok=True, parents=True)
            return path
        else:
            raise exp_dir("Unknown exp sub directory '{}'. Available subdirectories are: 'data', 'models', and 'logs'.")
    else:
        raise RuntimeError("No experiment reference has been set beforehand")
# End def exp_dir


def state_dir():
    if _SYSTEM in ('win32', 'darwin'):
        path = _APP_DIR.user_data_dir
    else:
        # XDG default for XDG_STATE_HOME
        path = os.path.join(
            os.getenv('XDG_STATE_HOME', os.path.expanduser('~/.local/state')),
            __FRAMEWORK_NAME__
        )
    if not os.path.exists(path):
        Path(path).mkdir(exist_ok=True, parents=True)
    return path


def log_dir():

    # MAC OSX
    if _SYSTEM in ("darwin", "win32"):
        path = _APP_DIR.user_log_dir
    else:
        path = os.path.join(state_dir(), "log")

    if not os.path.exists(path):
        Path(path).mkdir(exist_ok=True, parents=True)
    return path
# End def _log_dir
