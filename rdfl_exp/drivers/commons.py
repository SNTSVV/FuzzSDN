#!/usr/bin/env python3
"""
A utility class for common functions used accros all drivers
"""
# QUESTION: Should this module be moved to utils ?
from typing import Iterable

import pexpect

from rdfl_exp.config import DEFAULT_CONFIG as CONFIG


# TODO: Make logger specifically for this module
def sudo_expect(spawn: pexpect.spawn, pattern: Iterable = None, timeout: int = 180):
    """
    Wrapper around a pexpect.spawn command that require the usage of sudo

    :param spawn:   The pexpect.spawn object from which to expect the output
    :param pattern: The Iterable pattern list, default to None
    :param timeout:
    :return:
    """
    sudo_pattern = [r'password\sfor\s'] + list(pattern) if pattern is not None else [r'password\sfor\s']
    i = spawn.expect(sudo_pattern, timeout)

    if i == 0:
        # Sudo asking for password
        spawn.sendline(CONFIG.general.sudo_pwd)
        i = spawn.expect(pattern, timeout)
        return i
    else:
        # No need for sudo, just return i
        return i - 1
# End def sudo_expect
