#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Holds several functions that are use at different places in the code
"""

import os
import shutil


def is_type(value, _type) -> bool:
    """
    Check the type of a value.

    :param value: the value to be checked
    :param _type: the type that should be checked.
    :return bool: True if the values is of the type, False otherwise.
    """
    try:
        _type(value)
        return True
    except Exception:
        return False
# End def is_type


def str_to_typed_value(value):
    """Transform a string value to an actual data type of the same value. """
    if is_type(value, int):  # Int
        return int(value)
    elif is_type(value, float):  # Float
        return float(value)
    elif value.lower() in ['true', 'false', 'yes', 'no', 'on', 'off']:  # Boolean
        return True if value.lower() in ['true', 'yes', 'on'] else False
    elif is_type(value, None):  # None
        return None
    else:
        return value
# End def typed_value


def recursive_chown(path, owner, group=None):
    """
    Recursively change the owner of all the files in a folder
    :param path: path of the top level directory
    :param owner: uuid or name of the user that should become the owner
    :param group: guid or name of the group of the user that should become the owner (optional)
    """
    for dir_path, dir_names, filenames in os.walk(path):
        shutil.chown(dir_path, owner)
        for filename in filenames:
            shutil.chown(os.path.join(dir_path, filename), owner, group=group)
# End def recursive_chown
