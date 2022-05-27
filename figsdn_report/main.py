#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main script for figsdn-report
"""

import logging
import os
import sys
import traceback
from typing import Iterable, Optional

from tabulate import tabulate

from common import app_path
from common.utils import terminal
from common.utils.exit_codes import ExitCode
from common.utils.log import add_logging_level
from figsdn_report import arguments, experiment, nodes
from figsdn_report.arguments import Command


def parse_arguments(args: Optional[Iterable] = None):
    """
    Parse the arguments passed to the program.
    """
    return arguments.parse(sys.argv[1:] if args is None else args)
# End def parse_arguments


def main(args: Optional[Iterable] = None):

    # Parse the arguments
    args = parse_arguments(args)
    print(args)

    # Mandatory to avoid issue when using modules from the figsdn package
    add_logging_level('TRACE', logging.DEBUG - 5)

    # ===== [ List the experiments ] ======

    if args.command == Command.LIST_EXPT:
        if args.node is not None and args.node != 'local':

            target_node_list = []
            if args.node == 'all':
                target_node_list = nodes.list_saved_nodes()
            else:
                target_node_list.append(args.node)

            for target_node in target_node_list:
                # First check if the node is the known hosts
                node_dict = nodes.list_saved_nodes()
                if node_dict is not None:
                    node_list = list(node_dict.values())
                    for node in node_list:
                        if node['hostname'] == target_node:
                            args.rport = node['ssh_port']
                            args.ruser = node['username']
                            args.rpwd  = node['password']

                if args.ruser is None:
                    raise SystemExit("No user to connect to ssh into {}:{}".format(target_node, args.rport))
                if args.rpwd is None:
                    raise SystemExit("No password to connect to ssh into {}@{}:{}".format(args.ruser, target_node, args.rport))

                exps = nodes.list_remote_exp(hostname=target_node,
                                             ssh_port=args.rport,
                                             username=args.ruser,
                                             password=args.rpwd,
                                             quiet=True)
                if not exps:
                    print("No available experiment for {}@{}:{}".format(args.ruser, target_node, args.rport))
                else:
                    print("Available experiments for {}@{}:{}:".format(args.ruser, target_node, args.rport))
                    terminal.print_list_columns(exps)

        # List experiments for the local machine
        else:
            exps = os.listdir(os.path.join(app_path.data_dir(), 'experiments'))
            if not exps:
                print("No available experiment.".format(args.ruser, args.node, args.rport))
            else:
                print("Available experiments:".format(args.ruser, args.node, args.rport))
                terminal.print_list_columns(exps)

        # Exit the tool
        raise SystemExit(ExitCode.EX_OK)

    # ===== [ List the known hosts ] ======

    if args.command == Command.LIST_NODES:
        nodes_dict = nodes.list_saved_nodes()
        headers = ("No", "Hostname", "SSH Port", "Username", "Password")
        rows = list()
        if nodes_dict is not None:
            saved_nodes = list(nodes_dict.values())
            # Get the status
            print(saved_nodes)
            for i in range(len(saved_nodes)):
                rows.append((
                        "host_{}".format(i),
                        saved_nodes[i]['hostname'],
                        saved_nodes[i]['ssh_port'],
                        saved_nodes[i]['username'],
                        saved_nodes[i]['password'] if args.show_pass is True else '*'*len(saved_nodes[i]['password'])
                ))

        print(tabulate(tabular_data=rows,
                       headers=headers,
                       showindex=False))

    # ===== [ Add a node ] ======

    if args.command == Command.ADD_NODE:
        try:
            nodes.add(
                hostname=args.hostname,
                ssh_port=args.rport,
                username=args.user,
                password=args.rpwd,
                overwrite=args.overwrite
            )
        except Exception as e:
            print("Failed to add node {}@{}:{} with error:".format(args.user, args.hostname, args.rport),
                  file=sys.stderr)
            print(e, file=sys.stderr)
            raise SystemExit(ExitCode.EX_DATAERR)
        else:
            print("Successfully added node {}@{}:{}".format(args.user, args.hostname, args.rport))
            raise SystemExit(ExitCode.EX_OK)

    # ===== [ Remove a node ] ======

    if args.command == Command.RMV_NODE:
        try:
            # Remove all nodes
            if args.node == 'all':
                proceed = True
                if not args.assume_yes:
                    proceed = terminal.query_yes_no("Remove all remote nodes saved?")
                if proceed is True:
                    node_list = nodes.list_saved_nodes()
                    for node in node_list:
                        nodes.remove(node)
                else:
                    raise SystemExit(ExitCode.EX_OK)
            else:
                nodes.remove(args.node)
        except Exception:
            print("Failed to remove node '{}'".format(args.node), file=sys.stderr)
            traceback.print_exc()
            raise SystemExit(ExitCode.EX_DATAERR)
        else:
            if args.node == 'all':
                print("Successfully removed all registered nodes")
            else:
                print("Successfully removed node '{}'".format(args.node))
            raise SystemExit(ExitCode.EX_OK)

    # ===== [ Fetch an experiment ] ======

    if args.command == Command.GET_EXPT:

        # Parameters to fed to the experiment fetch module
        hostname        = args.node
        port            = 22
        user            = None
        password        = None
        expt_to_fetch   = args.expt

        # First check if the node is the known hosts
        node_dict = nodes.list_saved_nodes()
        if node_dict is not None:
            node_list = list(node_dict.values())
            for node in node_list:
                if node['hostname'] == hostname:
                    port = node['ssh_port']
                    user = node['username']
                    password = node['password']

        # Update the parameters if required
        if args.rport is not None and args.rport != port:
            port = args.rport
        if args.ruser is not None and args.ruser != user:
            user = args.ruser
        if args.rpwd is not None and args.rpwd != password:
            password = args.rpwd

        # Fetch the experiment
        print("Fetching experiment \"{}\" at {}@{}:{}".format(expt_to_fetch, user, hostname, port))
        experiment.fetch(
            hostname=hostname,
            port=port,
            username=user,
            password=password,
            expt=expt_to_fetch,
            debug=True
        )

# End def main


if __name__ == "__main__":
    main()