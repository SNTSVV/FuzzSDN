#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script is the entry point of figsdn cli app.
"""
import logging
import os
import sys
import traceback
from typing import Optional

from tabulate import tabulate

from figsdn import arguments, report
from figsdn.arguments import Command, ExperimentCommand, NodesCommand
from figsdn.common import app_path, nodes
from figsdn.common.utils import ExitCode, terminal, log
from figsdn.report.main import main as report_main
from figsdn.app.main import main as app_main


def main():

    # Mandatory to avoid issues with the log commands
    log.add_logging_level('TRACE', logging.DEBUG - 5)

    # Parse the arguments
    args = arguments.parse()

    # Deal with the experiments
    if args.cmd == Command.EXPERIMENT:

        # List the available experiments
        if args.expt_cmd == ExperimentCommand.LIST:
            list_available_experiments(node=args.node)

        # Report the results of an experiment
        elif args.expt_cmd == ExperimentCommand.REPORT:
            report_main(
                expt=args.expt,
                node=args.node,
                ignore_existing=args.ignore_existing,
                test_on_data=args.test_on_data
            )

        # List the available experiments
        elif args.expt_cmd == ExperimentCommand.RUN:
            app_main(
                scenario=args.scenario,
                criterion=args.criterion_name,
                target_class=args.target_class,
                other_class=args.other_class,
                samples=args.samples,
                method=args.method,
                budget=args.budget,
                ml_algorithm=args.algorithm,
                ml_filter=args.filter,
                ml_cv_folds=args.cv_folds,
                mutation_rate=args.mutation_rate,
                criterion_kwargs=args.criterion_kwargs,
                limit=args.limit,
                reference=args.reference
            )

        # List the Re experiments
        elif args.expt_cmd == ExperimentCommand.LIST:
            list_available_experiments(node=args.node)

    # Deal with the nodes
    elif args.cmd == Command.NODES:

        # List available nodes
        if args.nodes_cmd == NodesCommand.LIST:
            list_known_nodes(args.show_pass)

        # Add a new node
        elif args.nodes_cmd == NodesCommand.ADD:
            add_node(
                hostname=args.hostname,
                port=args.rport,
                user=args.user,
                pwd=args.rpwd,
                overwrite=args.overwrite
            )

        # Remove a node
        elif args.nodes_cmd == NodesCommand.REMOVE:
            remove_node(
                node=args.node,
                interactive=not args.assume_yes
            )

    else:  # This should be unreachable
        print("Unknown command \"{}\".".format(args.cmd), file=sys.stderr)
        raise SystemExit(ExitCode.EX_CMDNOTFOUND)
# End def main


def list_available_experiments(node : Optional[str]):

    if node is not None:
        target_node_list = []
        if node == 'all':
            target_node_list = nodes.list_saved_nodes()
        else:
            target_node_list.append(node)

        for target_node in target_node_list:
            # First check if the node is the known hosts
            node_dict = nodes.list_saved_nodes()
            ruser, rpwd, rport = None, None, None
            if node_dict is not None:
                node_list = list(node_dict.values())
                for node in node_list:
                    if node['hostname'] == target_node:
                        rport = node['ssh_port']
                        ruser = node['username']
                        rpwd  = node['password']

            if not ruser:
                raise SystemExit("No user to connect to ssh into {}:{}".format(target_node, rport))
            if not rpwd:
                raise SystemExit("No password to connect to ssh into {}@{}:{}".format(ruser, target_node, rport))

            exps = nodes.list_remote_exp(hostname=target_node,
                                         ssh_port=rport,
                                         username=ruser,
                                         password=rpwd,
                                         quiet=True)
            if not exps:
                print("No available experiment for {}@{}:{}".format(ruser, target_node, rport))
            else:
                print("Available experiments for {}@{}:{}:".format(ruser, target_node, rport))
                terminal.print_list_columns(exps)

    # List experiments for the local machine
    else:
        try:
            exps = os.listdir(os.path.join(app_path.data_dir(), 'experiments'))
            if not exps:
                print("No available experiment.")
            else:
                print("Available experiments:")
                terminal.print_list_columns(exps)
        except FileNotFoundError:
            print("No available experiment.")

    # Exit the tool
    raise SystemExit(ExitCode.EX_OK)
# End def list_available_experiments


def list_known_nodes(show_password : bool = False):

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
                saved_nodes[i]['password'] if show_password is True else '*' * len(saved_nodes[i]['password'])
            ))

    print(tabulate(tabular_data=rows,
                   headers=headers,
                   showindex=False))
# End def list_known_nodes


def add_node(hostname, port, user, pwd, overwrite : bool = False):
    try:
        nodes.add(
            hostname=hostname,
            ssh_port=port,
            username=user,
            password=pwd,
            overwrite=overwrite
        )
    except Exception as e:
        print("Failed to add node {}@{}:{} with error:".format(user, hostname, port), file=sys.stderr)
        print(e, file=sys.stderr)
        raise SystemExit(ExitCode.EX_DATAERR)
    else:
        print("Successfully added node {}@{}:{}".format(user, hostname, port))
        raise SystemExit(ExitCode.EX_OK)
# End def add_node


def remove_node(node : str, interactive=True):
    try:
        proceed = True

        # Remove all nodes
        if node == 'all':
            if interactive:
                proceed = terminal.query_yes_no("Remove all remote nodes saved ?")
            if proceed is True:
                node_list = nodes.list_saved_nodes()
                for node in node_list:
                    nodes.remove(node)
            else:
                print("No nodes removed.")
                raise SystemExit(ExitCode.EX_OK)
        else:
            if interactive:
                proceed = terminal.query_yes_no("Remove saved node \'{}\' ?".format(node))
            if proceed is True:
                nodes.remove(node)
            else:
                print("No nodes removed.")
                raise SystemExit(ExitCode.EX_OK)

    except Exception:
        print("Failed to remove node '{}'".format(node), file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(ExitCode.EX_DATAERR)
    else:
        if node == 'all':
            print("Successfully removed all registered nodes")
        else:
            print("Successfully removed node '{}'".format(node))
        raise SystemExit(ExitCode.EX_OK)
# End def remove_node