#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib
import json
import logging
import os
import signal
import subprocess
import sys
import time
import random

from fuzzsdn.app import setup
from fuzzsdn.app.drivers import FuzzerDriver, MininetDriver, OnosDriver
from fuzzsdn.common.utils.database import Database as SqlDb

# ===== ( Parameters ) =================================================================================================

logger = logging.getLogger(__name__)
exp_logger = logging.getLogger("PacketFuzzer.jar")


# ===== (Before, after functions) ======================================================================================


def initialize(**opts):
    """Job to be executed before the beginning of a series of test"""

    # Install onos
    logger.info("Installing ONOS...")
    installed = OnosDriver.install()
    if installed is not True:
        logger.error("Couldn't install ONOS")
        return False
    else:
        logger.debug("ONOS has been successfully installed.")


# End def initialize


def before_each(**opts):
    """Job before after each test."""

    success = True

    # Flush the logs of ONOS
    success &= OnosDriver.flush_logs()

    # Stop running instances of onos
    success &= OnosDriver.stop()

    # Start onos
    success &= OnosDriver.start()
    success &= OnosDriver.activate_app("org.onosproject.fwd")
    success &= OnosDriver.set_log_level("INFO")

    return success


# End def before_each


def after_each(**opts):
    """Job executed after each test."""

    if SqlDb.is_connected():
        logger.info("Disconnecting from the database...")
        SqlDb.disconnect()
        logger.info("Database is disconnected")

    # Clean mininet
    logger.info("Stopping Mininet")
    MininetDriver.stop()
    logger.debug("Done")

    logger.info("Stopping Control Flow Fuzzer")
    FuzzerDriver.stop(5)
    logger.debug("Done")

    OnosDriver.stop()
    logger.debug("done")


# End def after_each


def terminate(**opts):
    """Job to be executed after the end of a series of test"""
    OnosDriver.uninstall()


# End def terminate


# ===== ( Main test function ) =========================================================================================


def test(instruction=None, **opts):
    """Run the experiment

    Args:
        topo (str): The topology to choose.
    """

    # Write the instruction to the fuzzer
    logger.debug("Writing fuzzer instructions")
    if instruction is not None:
        FuzzerDriver.set_instructions(instruction)

    logger.info("Closing all previous instances on control flow fuzzer")

    # TODO: Use the FuzzerDriver instead
    for pid in get_pid("PacketFuzzer.jar"):
        os.kill(pid, signal.SIGKILL)

    logger.info("Starting Control Flow Fuzzer")
    FuzzerDriver.start()

    logger.info("Starting Mininet network")

    # Get the topo file
    topo_pkg = "fuzzsdn.resources.scenarios.{0}".format("onos_fully_connected_traffic")
    with importlib.resources.path(topo_pkg, 'topo.py') as p:
        topo_path = p

    # Start mininet with the topo
    topo = '1s_2h'  # Default topology
    if 'topo' in opts:
        topo = opts.get('topo', None)

    MininetDriver.start(
        cmd="mn --custom {}".format(topo_path.as_posix())
            + " --topo={}".format(topo)
            + " --controller=remote,ip={},port={},protocols=OpenFlow14".format(setup.config().onos.host,
                                                                               setup.config().fuzzer.port)
    )
    # Get all the nodes
    nodes = MininetDriver.nodes()
    logger.trace("Acquired nodes:\n{}".format(json.dumps(nodes, indent=4)))
    time.sleep(2)

    if nodes is not None:
        host_nodes = {key: nodes[key] for key in nodes.keys() if nodes[key]['type'] == 'host'}
        host1, host2 = random.sample(host_nodes.keys(), 2)  # Pick two random host from the list
        logger.info("Executing ping command: {} -> {}".format(host1, host2))
        stats = MininetDriver.ping_host(src=host1, dst=host2, count=1, wait_timeout=5)
        logger.trace("Ping results: {}".format(stats.as_dict() if stats is not None else stats))

    # TODO: Synchronize with fuzzer instead
    time.sleep(5)
# End def test


# ===== ( Utility Functions ) ==========================================================================================

def get_pid(name: str):
    """ Search the PID of a program by its partial name"""
    processes = subprocess.check_output(["ps", "-fea"]).decode(
        sys.stdout.encoding).split('\n')
    for p in processes:
        args = p.split()
        for part in args:
            if name in part:
                yield int(args[1])
                break
# End def get_pid
