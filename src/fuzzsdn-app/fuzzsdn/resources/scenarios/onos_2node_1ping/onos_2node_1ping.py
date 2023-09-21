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
exp_logger                  = logging.getLogger("PacketFuzzer.jar")

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
    success &= OnosDriver.set_log_level("DEBUG")

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
    for pid in get_pid("PacketFuzzer.jar"):
        os.kill(pid, signal.SIGKILL)

    logger.info("Starting Control Flow Fuzzer")
    FuzzerDriver.start()

    logger.info("Starting Mininet network")

    MininetDriver.start(
        cmd='mn --controller=remote,ip={},port={},protocols=OpenFlow14 --topo=single,2'.format(setup.config().onos.host,
                                                                                               setup.config().fuzzer.port)
    )

    logger.info("Executing ping command: h1 -> h2")
    stats = MininetDriver.ping_host(src='h1', dst='h2', count=1, wait_timeout=5)
    logger.trace("Ping results: {}".format(stats.as_dict() if stats is not None else stats))
    # TODO: Synchronize with fuzzer instead
    time.sleep(5)

# End def test


# ===== ( Utility Functions ) ==========================================================================================

def count_db_entries():

    count = 0
    try:
        if not SqlDb.is_connected():
            SqlDb.connect("control_flow_fuzzer")
        # Storing a new log message stating that onos crashed
        SqlDb.execute("SELECT COUNT(*) FROM fuzzed_of_message")
        SqlDb.commit()
        count = SqlDb.fetchone()[0]
    except (Exception,):
        logger.exception("An exception happened while recording mininet crash:")
    finally:
        SqlDb.disconnect()

    return count
# End def count_db_entries


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
