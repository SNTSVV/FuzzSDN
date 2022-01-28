#!/usr/bin/env python3
import logging
import os
from configparser import ConfigParser

from appdirs import AppDirs

# ===== ( Config Section ) =============================================================================================

class ConfigurationSection(object):

    def __init__(self, name, parser):
        self.__name = name
        self.__parser = parser
        self.__cache = dict()
    # End def __init__

    def __getattr__(self, option):
        if self.__parser.has_option(self.__name, option):
            if option not in self.__cache:
                self.__cache[option] = _typed_value(self.__parser.get(self.__name, option))
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


# ===== ( Config ) =====================================================================================================

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


# ===== ( Utility functions ) ==========================================================================================

def _is_type(value, _type):
    """Simply check the type of a value."""
    try:
        _type(value)
        return True
    except Exception:
        return False
# End def _is_type


def _typed_value(value):
    """ Transform a string value to an actual data type of the same value. """
    if _is_type(value, int):  # Int
        return int(value)
    elif _is_type(value, float):  # Float
        return float(value)
    elif value.lower() in ['true', 'false', 'yes', 'no', 'on', 'off']:  # Boolean
        return True if value.lower() in ['true', 'yes', 'on'] else False
    elif _is_type(value, None):  # None
        return None
    else:
        return value
# End def _typed_value


# ===== ( Setup configuration ) ========================================================================================

# Load the application directories
app_dirs = AppDirs("rdfl_exp")

# Load a global object named DEFAULT_CONFIG
if not os.path.exists(app_dirs.user_config_dir):
    os.mkdir(app_dirs.user_config_dir)

DEFAULT_CONFIG = None
if os.path.exists(os.path.join(app_dirs.user_config_dir, "rdfl_exp.cfg")):
    DEFAULT_CONFIG = Configuration(os.path.join(app_dirs.user_config_dir, "rdfl_exp.cfg"))
elif os.path.exists(os.path.join(app_dirs.site_config_dir, "rdfl_exp.cfg")):
    DEFAULT_CONFIG = Configuration(os.path.join(app_dirs.site_config_dir, "rdfl_exp.cfg"))
else:
    raise FileNotFoundError("Couldn't find configuration file \"rdfl_exp.cfg\" neither under \"{}\" nor \"{}\"".format(
        os.path.join(app_dirs.user_config_dir, "rdfl_exp.cfg"),
        os.path.join(app_dirs.site_config_dir, "rdfl_exp.cfg")
    ))

# Had a trace level to logging module
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

