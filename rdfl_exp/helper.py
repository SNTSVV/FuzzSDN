#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collection of helping functions for rdfl_exp
"""

import getpass
import os
import pwd
import tempfile


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
