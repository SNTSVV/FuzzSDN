# -*- coding: utf-8 -*-
"""
Module used to parse the arguments of figsdn-report
"""

import argparse
from typing import Iterable, Optional

from figsdn import __version__ as __figsdn_version__, __app_name__ as __figsdn_name__
from figsdn_report import __version__, __app_name__
from common.utils.str_enum import StrEnum


class Command(StrEnum):

    # Values
    LIST_EXPT   = 'list-expt',
    GET_EXPT    = 'get-expt',
    LIST_NODES  = 'list-node',
    ADD_NODE    = 'add-node',
    RMV_NODE    = 'remove-node',

    @staticmethod
    def all():
        """Returns a list of all the possible commands"""
        return list(map(lambda c: c.value, Command))


def parse(args: Optional[Iterable]):
    """
    Parse the arguments passed to the program.
    """
    parser = argparse.ArgumentParser(description="Report tool for FIGSDN.")

    # ===== ( Optional Arguments ) ======

    # Fetch the results from a remote node
    parser.add_argument(
        '-y',
        '--yes',
        '--assume-yes',
        dest='assume_yes',
        help="Automatic yes to prompts; assume \"yes\" as answer to all prompts and run non-interactively.",
        action='store_true',
    )

    parser.add_argument(
        '--version',
        action='version',
        version='{} {} (from {} {})'.format(__app_name__, __version__, __figsdn_name__, __figsdn_version__)
    )

    # ===== ( Positional arguments ) =========

    command_parser = parser.add_subparsers(
        title='command',
        dest='command',
        required=True,
        metavar='COMMAND',
        help="Command to be executed."
    )

    # ==== ( Args for command LIST_NODES ) =========

    list_node_cmd = command_parser.add_parser(
        name=Command.LIST_NODES,
        help='List all previously saved remote nodes'
    )

    list_node_cmd.add_argument(
        '--show-pass',
        action='store_true',
        dest='show_pass',
        help="Display the passwords of the saved nodes in the console.",
        required=False
    )

    # ==== ( Args for command LIST_EXPT ) =========

    list_expt_cmd = command_parser.add_parser(
        name=Command.LIST_EXPT,
        help='List all the experiments in on a node.'
    )

    # Fetch the results from a remote node
    list_expt_cmd.add_argument(
        'node',
        nargs='?',
        help="Node to fetch the experiment from. Optional, default to local.",
        type=str,
    )

    list_expt_cmd.add_argument(
        '-s',
        '--ssh-port',
        metavar='port',
        action='store',
        default=22,  # Default ssh port on most machines
        dest="rport",
        type=int,
        required=False,
        help="Port used for SSH operations."
    )

    # User
    list_expt_cmd.add_argument(
        '-u',
        '--user',
        metavar='user',
        action='store',
        default=None,
        dest="ruser",
        type=str,
        required=False,
        help="User for SSH operations."
    )

    # Password
    list_expt_cmd.add_argument(
        '-p',
        '--password',
        metavar="pwd",
        type=str,
        default=None,
        dest='rpwd',
        help="Password to SSH into the remote node. Used only if --remote is used."
    )

    # ==== ( Args for command ADD_NODE ) =========

    add_node_cmd = command_parser.add_parser(
        name=Command.ADD_NODE,
        help='Add a remote node to the list of known modes'
    )

    # Fetch the results from a remote node
    add_node_cmd.add_argument(
        'hostname',
        help="Hostname of the node",
        type=str,
    )

    add_node_cmd.add_argument(
        'user',
        help="user to ssh into",
        type=str,
    )

    add_node_cmd.add_argument(
        '-s',
        '--ssh-port',
        action='store',
        default=22,  # Default ssh port on most machines
        dest="rport",
        type=int,
        required=False
    )

    # Password
    add_node_cmd.add_argument(
        '-p',
        '--password',
        type=str,
        default=None,
        dest='rpwd',
        help="Password to SSH into the remote node. Used only if --remote is used."
    )

    add_node_cmd.add_argument(
        '-o',
        '--overwrite',
        action='store_true',
        dest='overwrite',
        help="Overwrites the information of a previous node if it exists."
    )

    # ==== ( Args for command RMV_NODE ) =========

    rmv_node_cmd = command_parser.add_parser(
        name=Command.RMV_NODE,
        help='Remove a node from the list of known modes'
    )

    # Fetch the results from a remote node
    rmv_node_cmd.add_argument(
        'node',
        help="Saved node to remove. Accepted values are either the name of the node, its hostname or 'all'.",
        type=str,
    )

    # ==== ( Args for command GET_EXPT ) =========

    get_expt_cmd = command_parser.add_parser(
        name=Command.GET_EXPT,
        help='Fetch an experiment'
    )

    # Fetch the results from a remote node
    get_expt_cmd.add_argument(
        'node',
        help="Either the name of the node or a hostname.",
        type=str,
    )

    # Fetch the results from a remote node
    get_expt_cmd.add_argument(
        'expt',
        help="Name of the experiment to fetch",
        type=str,
    )

    # Force to tool fetch again the already downloaded experiments
    get_expt_cmd.add_argument(
        '--ignore-existing',
        action='store_true',
        dest='ignore_existing',
        help="Skip updating the datasets and models files that have already been downloaded beforehand."
    )

    get_expt_cmd.add_argument(
        '-t',
        '--test-on-data',
        dest='test_on_data',
        default=None,
        help="If a test to perform is added to the list,"
    )

    get_expt_cmd.add_argument(
        '-u',
        '--user',
        dest='ruser',
        help="User of the node to ssh into",
        type=str,
    )

    get_expt_cmd.add_argument(
        '-s',
        '--ssh-port',
        action='store',
        default=22,  # Default ssh port on most machines
        dest="rport",
        type=int,
        required=False
    )

    # Password
    get_expt_cmd.add_argument(
        '-p',
        '--password',
        type=str,
        default=None,
        dest='rpwd',
        help="Password to SSH into the remote node. Used only if --remote is used."
    )

    # Finally, parse the arguments
    return parser.parse_args(args)
# End def parse
