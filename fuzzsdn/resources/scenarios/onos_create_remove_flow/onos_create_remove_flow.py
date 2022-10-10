#!/usr/bin/env python3
# coding: utf-8
import logging
import os
import signal
import subprocess
import sys
import time

from fuzzsdn.app import setup
from fuzzsdn.app.drivers import FuzzerDriver, MininetDriver, OnosDriver
from fuzzsdn.common.utils.database import Database as SqlDb

# ===== ( Parameters ) =================================================================================================

logger                      = logging.getLogger(__name__)
exp_logger                  = logging.getLogger("fuzzsdn-fuzzer.jar")

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
    for pid in get_pid("fuzzsdn-fuzzer.jar"):
        os.kill(pid, signal.SIGKILL)

    logger.info("Starting Control Flow Fuzzer")
    FuzzerDriver.start()

    logger.info("Starting Mininet network")

    MininetDriver.start(
        cmd='mn --controller=remote,ip={},port={},protocols=OpenFlow14 --topo=single,2'.format(setup.config().onos.host,
                                                                                               setup.config().fuzzer.port)
    )

    # Add a flow between h1 and h2
    logger.info("Adding a flow to s1.")
    MininetDriver.add_flow(sw='s1',
                           flow="dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00:00:02,actions=output:2",
                           timeout=15.0)
    time.sleep(2)
    logger.info("Removing all flows from s1.")
    MininetDriver.delete_flow(sw='s1', strict=False)

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
