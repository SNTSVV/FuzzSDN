#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module that takes care of retrieving information about a remote VM used for experimentation.

The information about the remote VMs are stored locally in the state directory
"""
import json
import os
from pathlib import Path
from typing import Optional

import paramiko

from fuzzsdn.common import app_path

_REMOTE_VMS_FILE = os.path.join(app_path.state_dir(), "remote_vms.json")


# ===== (  ) ===========================================================================================================

def list_saved_nodes() -> Optional[dict]:
    vms = None
    if os.path.exists(_REMOTE_VMS_FILE):
        with open(_REMOTE_VMS_FILE, 'r') as vms_file:
            vms = json.load(vms_file)
            if not vms:
                vms = None
    return vms
# End def get_info


def list_remote_exp(hostname: str, ssh_port: int, username: str, password: Optional[str] = None, quiet=False):

    if not quiet:
        print("Establishing SSH connection to {}@{}:{}".format(username, hostname, ssh_port))

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, ssh_port, username, password)

    # Get the user home directory
    _, stdout, _ = ssh.exec_command("eval echo ~$USER")
    usr_home = stdout.readlines()[0].strip()

    # List all the experiments that can be listed
    # TODO: Find a way to automatically find the remote exp_path.
    #       Maybe by writing it to a file or something...
    stdin, stdout, stderr = ssh.exec_command("ls {}/.local/share/fuzzsdn/experiments".format(usr_home))
    return list(sorted([x.strip() for x in stdout.readlines()]))
# End def list_remote_exp


def add(hostname: str, ssh_port: int, username: str, name: Optional[str] = None, password: Optional[str] = None,
        overwrite=False):
    """
    Save a configuration about the remote host
    :param name:
    :param hostname:
    :param ssh_port:
    :param username:
    :param password:
    :param overwrite:
    :return:
    """
    # Get the name to register the vm as
    vm_name = name if name is not None else hostname

    # Prepare the new entry
    entry = {
        'hostname': hostname,
        'ssh_port': ssh_port,
        'username': username,
        'password': password
    }

    vms = dict()
    if os.path.exists(_REMOTE_VMS_FILE):
        vms = list_saved_nodes()
        # If there is no vms register then
        if vms is None:
            vms = dict()

    # Check if there is already an entry for the VM
    already_exists = False
    known_vm_name = None
    if vms is not None:
        if vm_name in vms:
            already_exists = True
            known_vm_name = vm_name
        else:
            for _name in vms.keys():
                if hostname in vms[_name]:
                    already_exists = True
                    known_vm_name = _name
                    break

    # If overwrite is not set, then throw an exception
    if overwrite is False and already_exists is True:
        if known_vm_name == vm_name:
            except_msg = "Cannot register VM \"{}\". There is already a VM with the same name (host: {}).".format(
                vm_name,
                vms[vm_name]['hostname']
            )
        else:
            except_msg = "Cannot register VM \"{}\".There is already a VM ({}) with the same host ({})".format(
                vm_name,
                known_vm_name,
                hostname
            )
        raise ValueError(except_msg)

    if already_exists:
        del vms[known_vm_name]

    vms[vm_name] = entry

    # Sets the full path
    Path(_REMOTE_VMS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(_REMOTE_VMS_FILE, 'w') as vms_file:
        json.dump(vms, vms_file, indent=4, sort_keys=True)
# End def add


def remove(hostname: str):
    """
    Remove a VM from the configuration,
    First check the names then the hostnames.

    :param hostname:
    :raise ValueError: If couldn't find

    :return:
    """

    try:
        with open(_REMOTE_VMS_FILE, 'r') as vm_file:
            vms = json.load(vm_file)
    except OSError:  # OSError is raised when no VMs are registered
        raise ValueError("No remote VMs registered.")

    deleted = False

    # Check if there is already an entry for the VM
    for k, v in vms.items():
        if v['hostname'] == hostname:
            del vms[k]
            deleted = True
            break

    if deleted is True:
        with open(_REMOTE_VMS_FILE, 'w') as vms_file:
            json.dump(vms, vms_file, indent=4, sort_keys=True)
    else:
        raise ValueError("No VMs with name or hostname \"{}\"".format(hostname))
# End def remove
