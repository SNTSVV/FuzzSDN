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
# End def str_to_typed_value


# ===== (dict and list) ================================================================================================


def dict_replace(obj: dict, old, new) -> dict:
    """
    Replace all the elements in a dictionary with a certain value, no matter the key.

    :param obj: The dict to perform the replacement on
    :param old: The value to be replaced
    :param new: The new value to replace
    """
    x = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            v = dict_replace(v, old, new)
        elif isinstance(v, list):
            v = list_replace(v, old, new)
        elif v == old:
            v = new
        x[k] = v
    return x
# End def dict_replace


def list_replace(obj: list, old, new) -> list:
    """
    Replace all the elements in a list with a certain value, no matter the key.

    :param obj: The list to perform the replacement on
    :param old: The value to be replaced
    :param new: The new value to replace
    """

    x = []
    for e in obj:
        if isinstance(e, list):
            e = list_replace(e, old, new)
        elif isinstance(e, dict):
            e = dict_replace(e, old, new)
        elif e == old:
            e = new
        x.append(e)
    return x
# End def list_replace


def normalize(arr):
    """Normalize an iterable"""

    xmin = min(arr)
    xmax = max(arr)
    return [(x - xmin)/(xmax - xmin) for x in arr]
# End def normalize

# ===== ( Files ) ======================================================================================================

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


def check_and_rename(file_path):
    if os.path.exists(file_path):
        num = 1
        while True:
            new_path = "{0}_{2}{1}".format(*os.path.splitext(file_path) + (num,))
            if os.path.exists(new_path):
                num += 1
            else:
                return new_path
    return file_path
# End def check_and_rename
