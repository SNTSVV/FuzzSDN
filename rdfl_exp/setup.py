#!/usr/bin/env python3
import logging
import os
import pwd
import tempfile
from configparser import ConfigParser
from datetime import datetime
import getpass
from pathlib import Path
from typing import Optional

from appdirs import AppDirs

from common.utils.log import add_logging_level
from common.utils import check_and_rename, str_to_typed_value
from common.utils.terminal import Fore, Style

# ===== ( Globals definition ) ===========================================================================================

CONFIG          = None
APP_DIR         : Optional[AppDirs] = None
EXP_REF         = ""
EXP_DIR         : Optional[str] = None
EXP_DATA_DIR    : Optional[str] = None
EXP_LOG_DIR     : Optional[str] = None
EXP_MODELS_DIR  : Optional[str] = None


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

def init(args=None):

    global APP_DIR
    global CONFIG
    global EXP_REF

    # Load the application directories
    APP_DIR = AppDirs("rdfl_exp")

    # Load the configuration
    if not os.path.exists(APP_DIR.user_config_dir):
        os.mkdir(APP_DIR.user_config_dir)
    if os.path.exists(os.path.join(APP_DIR.user_config_dir, "rdfl_exp.cfg")):
        CONFIG = Configuration(os.path.join(APP_DIR.user_config_dir, "rdfl_exp.cfg"))
    elif os.path.exists(os.path.join(APP_DIR.site_config_dir, "rdfl_exp.cfg")):
        CONFIG = Configuration(os.path.join(APP_DIR.site_config_dir, "rdfl_exp.cfg"))
    else:
        raise FileNotFoundError(
            "Couldn't find configuration file \"rdfl_exp.cfg\" neither under \"{}\" nor \"{}\"".format(
                os.path.join(APP_DIR.user_config_dir, "rdfl_exp.cfg"),
                os.path.join(APP_DIR.site_config_dir, "rdfl_exp.cfg")
            ))

    if args is not None and hasattr(args, 'reference'):
        EXP_REF = str(args.reference).strip()

    _make_folder_struct()
    _configure_pid()
    _configure_logger()
# End def make_folder_struct


# ===== ( Directories ) ================================================================================================

def app_dir() -> Optional[AppDirs]:
    return APP_DIR
# End def app_dir


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


def exp_dir(directory: Optional[str] = None) -> Optional[str]:
    if directory is None or directory == '':
        return EXP_DIR
    elif directory.lower() == 'data':
        return EXP_DATA_DIR
    elif directory.lower() == 'models':
        return EXP_MODELS_DIR
    elif directory.lower() == 'logs':
        return EXP_LOG_DIR
    else:
        raise exp_dir("Unknown exp_dir '{}'. Available exp_dir are: 'data', 'models', and 'logs'.")
# End def get_config


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


# ===== ( Private config functions ) ===========================================

def _make_folder_struct():
    """
    Create the folder structure.
    """
    global EXP_DIR
    global EXP_REF
    global EXP_DATA_DIR
    global EXP_MODELS_DIR
    global EXP_LOG_DIR

    # 1. Define the experiments dir, path, etc
    now             = datetime.now().strftime("%Y%m%d_%H%M%S")
    EXP_DIR         = os.path.join(APP_DIR.user_data_dir, 'experiments', now if not EXP_REF else EXP_REF)
    EXP_DIR         = check_and_rename(EXP_DIR)
    EXP_DATA_DIR    = os.path.join(EXP_DIR, 'data')
    EXP_MODELS_DIR  = os.path.join(EXP_DIR, 'models')
    EXP_LOG_DIR     = os.path.join(EXP_DIR, 'logs')

    # 2. Create the user data dir and it's sub folders
    try:
        # Data path
        Path(APP_DIR.user_data_dir).mkdir(parents=True, exist_ok=True)
        Path(EXP_DIR).mkdir(parents=True, exist_ok=False)
        Path(EXP_DATA_DIR).mkdir(parents=False, exist_ok=False)
        Path(EXP_MODELS_DIR).mkdir(parents=False, exist_ok=False)
        Path(EXP_LOG_DIR).mkdir(parents=False, exist_ok=False)
    except Exception:
        raise SystemExit(
            Fore.RED + Style.BOLD + "Error" + Style.RESET
            + ": Cannot create user data directory at \"{}\". ".format(APP_DIR.user_data_dir)
        )

    # 3. Create cache directory
    try:
        # cache directory
        Path(APP_DIR.user_cache_dir).mkdir(parents=True, exist_ok=True)
        # log directory
        Path(APP_DIR.user_log_dir).mkdir(parents=True, exist_ok=True)
    except Exception:
        raise SystemExit(
            Fore.RED + Style.BOLD + "Error" + Style.RESET
            + ": Cannot create directories at \"{}\". ".format(APP_DIR.user_cache_dir)
            + "Please verify the script got root permissions"
        )

    # 4. Create the log directory
    try:
        Path(APP_DIR.user_log_dir).mkdir(parents=True, exist_ok=True)
    except Exception:
        raise SystemExit(
            Fore.RED + Style.BOLD + "Error" + Style.RESET
            + ": Cannot create log directory at \"{}\". ".format(APP_DIR.user_log_dir)
        )
# End def _make_folder_struct


def _configure_pid():
    """
    Check the presence of a pid file and verify if another experiment isn't
    running.
    """

    pid_filepath = os.path.join(APP_DIR.user_cache_dir, "rdfl_exp.pid")

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


def _configure_logger():

    global EXP_REF

    # Add the trace level
    add_logging_level(level_name='TRACE', level_num=logging.DEBUG-5)

    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Write the header into the new log file
    log_file = os.path.join(APP_DIR.user_log_dir, config().logging.filename)
    with open(log_file, 'w') as f:
        header = "\n".join([
            "############################################################################################################",
            "App Name   : {}".format("RDFL_EXP v0.3.0"),
            "PID        : {}".format(os.getpid()),
            "Reference  : {}".format(datetime.now() if not EXP_REF else EXP_REF),
            "Start Date : {}".format(datetime.now()),
            "============================================================================================================\n"
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
        datefmt='%H:%M:%S',
        level=level
    )
# End def _setup_logger
