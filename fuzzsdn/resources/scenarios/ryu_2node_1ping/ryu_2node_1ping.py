#!/usr/bin/env python3
# coding: utf-8
import logging
import os
import signal
import subprocess
import sys
import time

from fuzzsdn.app import setup
from fuzzsdn.app.drivers import FuzzerDriver, MininetDriver, RyuDriver

# ===== ( Parameters ) =================================================================================================

logger                      = logging.getLogger(__name__)
exp_logger                  = logging.getLogger("PacketFuzzer.jar")

# ===== (Before, after functions) ======================================================================================


def initialize(**opt):
    """Job to be executed before the beginning of a series of test"""
    pass
# End def initialize


def before_each(**opt):
    """Job before after each test."""

    success = True

    # Flush the logs of ONOS
    success &= RyuDriver.flush_logs()

    # Stop running instances of onos
    success &= RyuDriver.stop()

    # Start onos
    success &= RyuDriver.start('ryu.app.simple_switch_14')
    time.sleep(2)
    return success
# End def before_each


def after_each(**opt):
    """Job executed after each test."""

    # Clean mininet
    logger.info("Stopping Mininet")
    MininetDriver.stop()
    logger.debug("Done")

    logger.info("Stopping Control Flow Fuzzer")
    FuzzerDriver.stop(5)
    logger.debug("Done")

    RyuDriver.stop()
    time.sleep(2)
    logger.debug("done")
# End def after_each


def terminate(**opt):
    """Job to be executed after the end of a series of test"""
    pass
# End def terminate


# ===== ( Main test function ) =========================================================================================


def test(instruction=None, **opt):
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
    for pid in get_pid("fuzzsdn-fuzzer.jar"):
        os.kill(pid, signal.SIGKILL)

    logger.info("Starting Control Flow Fuzzer")
    FuzzerDriver.start()
    time.sleep(5)

    logger.info("Starting Mininet network")

    MininetDriver.start(
        cmd='mn --controller=remote,ip={},port={},protocols=OpenFlow14 --topo=single,2'.format(setup.config().ryu.host,
                                                                                               setup.config().fuzzer.port)
    )

    logger.info("Executing ping command: h1 -> h2")
    stats = MininetDriver.ping_host(src='h1', dst='h2', count=1, wait_timeout=5)

    logger.trace("Ping results: {}".format(stats.as_dict() if stats is not None else stats))
    time.sleep(5)

# End def run_fuzz_test


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
