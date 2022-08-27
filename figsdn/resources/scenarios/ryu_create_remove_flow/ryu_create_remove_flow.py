#!/usr/bin/env python3
# coding: utf-8
import logging
import os
import signal
import subprocess
import sys
import time

from figsdn.app import setup
from figsdn.app.drivers import FuzzerDriver, MininetDriver, RyuDriver
from figsdn.common.utils.database import Database as SqlDb

# ===== ( Parameters ) =================================================================================================

logger                      = logging.getLogger(__name__)
exp_logger                  = logging.getLogger("figsdn-fuzzer.jar")

# ===== (Before, after functions) ======================================================================================


def initialize(**opts):
    """Job to be executed before the beginning of a series of test"""
    return True
# End def initialize


def before_each(**opts):
    """Job before after each test."""

    success = True

    # Flush the logs of ONOS
    success &= RyuDriver.flush_logs()

    # Stop running instances of ryu
    success &= RyuDriver.stop()

    # Start Ryu
    success &= RyuDriver.start('ryu.app.simple_switch_14')
    time.sleep(2)

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

    logger.info("Stopping fuzzer Fuzzer")
    FuzzerDriver.stop(5)
    logger.debug("Done")

    RyuDriver.stop()
    logger.debug("done")
# End def after_each


def terminate(**opts):
    """Job to be executed after the end of a series of test"""
    return True
# End def terminate


# ===== ( Main test function ) =========================================================================================


def test(instruction=None, **opts):
    """
    Run the experiment
    :param instruction:
    :return:
    """

    # Write the instruction to the fuzzer
    logger.debug("Writing fuzzer instructions")
    if instruction is not None:
        FuzzerDriver.set_instructions(instruction)

    logger.info("Closing all previous instances on control flow fuzzer")

    # TODO: Use the FuzzerDriver instead
    for pid in get_pid("figsdn-fuzzer.jar"):
        os.kill(pid, signal.SIGKILL)

    logger.info("Starting Control Flow Fuzzer")
    FuzzerDriver.start()

    logger.info("Starting Mininet network")

    MininetDriver.start(
        cmd='mn --controller=remote,ip={},port={},protocols=OpenFlow14 --topo=single,2'.format(setup.config().onos.host,
                                                                                               setup.config().fuzzer.port)
    )
    time.sleep(5)
    # Add a flow between h1 and h2
    logger.info("Adding a flow to s1.")
    MininetDriver.add_flow(sw='s1',
                           flow="dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00:00:02,actions=output:2",
                           timeout=15.0)
    time.sleep(5)
    logger.info("Removing all flows from s1.")
    MininetDriver.delete_flow(sw='s1', strict=True)

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
