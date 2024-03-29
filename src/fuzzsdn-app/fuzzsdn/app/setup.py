# -*- coding: utf-8 -*-
"""
Module to setup fuzzsdn application.
"""
import getpass
import logging
import os
import pwd
from configparser import ConfigParser
from datetime import datetime
from typing import Optional, Union

from fuzzsdn.common import app_path
from fuzzsdn.common.utils import str_to_typed_value
from fuzzsdn.common.utils.log import add_logging_level
from fuzzsdn.common.utils.terminal import Fore, Style

from fuzzsdn import __version__, __app_name__

# ===== ( Globals definition ) ===========================================================================================

CONFIG              = None
CONFIG_NAME         = "{}.cfg".format(__app_name__)
EXP_REF             = ""
_IS_INIT            = False

# ===== ( Config Section class ) =======================================================================================

class ConfigurationSection(object):

    def __init__(self, name, parser):
        self.__name = name
        self.__parser = parser
        self.__cache = dict()
    # End def __init__

    def __getattr__(self, option):
        if self.__parser.has_option(self.__name, option):
            if option not in self.__cache:
                self.__cache[option] = str_to_typed_value(self.__parser.get(self.__name, option))
            return self.__cache[option]
        else:
            raise KeyError("No option \"{}\" in section: \"{}\"".format(option, self.__name))
    # End def __getattr__

    def __getitem__(self, option):
        return self.__getattr__(option)
    # End def __getitem__

    def __dir__(self):
        return self.__parser.options(self.__name)

    # End def __getattr__
# End class ConfigurationSection


class Configuration:
    """
    Configuration class that read a configuration file
    """

    def __init__(self, file_name):
        self.__file_name = file_name
        self.__parser = ConfigParser()
        self.__cache = dict()

        # Read the configuration file
        self.__parser.read(file_name)
    # End def init

    def __getattr__(self, section):
        if self.__parser.has_section(section):
            if section not in self.__cache:
                self.__cache[section] = ConfigurationSection(section, self.__parser)
            return self.__cache[section]
        else:
            raise KeyError("No section \"{}\" in config".format(section, self))
    # End def __getattr__

    def __getitem__(self, key):
        return self.__getattr__(key)
    # End def __getitem__

    def __dir__(self):
        return [k for k in self.__parser.keys() if k != 'DEFAULT']

    def save(self):
        with open(self.file_name, 'w') as f:
            self.__parser.write(f)
        f.close()
    # End def save
# End class Config


# ===== ( Init ) =======================================================================================================

def init(expt_reference : Optional[Union[str, int, float]] = None):

    global CONFIG
    global EXP_REF
    global _IS_INIT

    # Verify that there is a configuration file in the configuration directory
    config_path = os.path.join(app_path.config_dir(), CONFIG_NAME)
    if os.path.exists(config_path):
        CONFIG = Configuration(config_path)
    else:
        raise FileNotFoundError(
            "Couldn't find configuration file \"{}\"  under \"{}\"".format(CONFIG_NAME, config_path))

    # Parse the reference
    if expt_reference is not None:
        EXP_REF = str(expt_reference).strip()
    else:
        EXP_REF = datetime.now().strftime("%Y%d%m_%H%M%S")
    app_path.set_experiment_reference(EXP_REF)

    _configure_pid()
    _configure_logger()

    _IS_INIT = True
# End def make_folder_struct


def is_initialized() -> bool:
    return _IS_INIT
# End def is_initialized


# ===== ( Functions ) ==================================================================================================

def config() -> Optional[Configuration]:
    return CONFIG
# End def config


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


def pid_path():
    """Returns the path to the pid file."""
    return os.path.join(app_path.run_dir(), "{}.pid".format(__app_name__))
# Emd def pid_path


# ===== ( Private config functions ) ===========================================

def _configure_pid():
    """
    Check the presence of a pid file and verify if another experiment isn't
    running.
    """

    pid_file = os.path.join(app_path.run_dir(), "{}.pid".format(__app_name__))

    if os.path.isfile(pid_file):
        # There is a PID
        with open(pid_file, 'r') as pf:
            pid = int(pf.readline().rstrip())

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

                os.remove(pid_file)

    # If there is no pid we create one for this program
    with open(pid_file, 'w') as pf:
        pf.write(str(os.getpid()))
# End def +_setup_pid


def _configure_logger():

    global EXP_REF

    # Add the trace level
    if not hasattr(logging, 'trace'):
        add_logging_level(level_name='TRACE', level_num=logging.DEBUG-5)

    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Write the header into the new log file
    try:
        prefix = "{}-".format(config().logging.file_prefix)
    except KeyError:
        prefix = ''

    log_file = os.path.join(app_path.log_dir(), "{}{}.log".format(prefix, EXP_REF))

    with open(log_file, 'w') as f:
        header = "\n".join([
            "#"*100,
            "App Name   : {}".format("{} v{}").format(__app_name__.upper(), __version__),
            "PID        : {}".format(os.getpid()),
            "Exp Ref    : {}".format(EXP_REF),
            "Start Date : {}".format(datetime.now()),
            "="*100
        ])
        f.writelines(header)

    # Add the configuration
    level_d = {
        'TRACE' : logging.TRACE if hasattr(logging, 'TRACE') else logging.DEBUG,
        'DEBUG' : logging.DEBUG,
        'INFO'  : logging.INFO,
        'WARN'  : logging.WARNING,
        'ERROR' : logging.ERROR
    }
    level = level_d.get(config().logging.level, logging.INFO)
    logging.basicConfig(
        filename=log_file,
        filemode='a',  # Use append affix to not overwrite the header
        format='%(asctime)s,%(msecs)d | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=level
    )
# End def _setup_logger
