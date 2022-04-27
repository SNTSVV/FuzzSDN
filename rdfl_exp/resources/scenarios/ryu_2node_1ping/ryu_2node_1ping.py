#!/usr/bin/env python3
# coding: utf-8
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

from rdfl_exp import setup
from rdfl_exp.drivers import FuzzerDriver, MininetDriver, RyuDriver
from common.utils.database import Database as SqlDb
from common.utils.exit_codes import ExitCode

# ===== ( Parameters ) =================================================================================================

logger                      = logging.getLogger(__name__)
exp_logger                  = logging.getLogger("PacketFuzzer.jar")

# ===== (Before, after functions) ======================================================================================


def initialize():
    """Job to be executed before the beginning of a series of test"""

    # Connect to the database
    database_is_init = False
    if not SqlDb.is_init():
        logger.info("Initializing the SQL database...")
        SqlDb.init(setup.config().mysql.host,
                   setup.config().mysql.user,
                   setup.config().mysql.password)
        logger.debug("The SQL database has been initialized successfully")

    try:
        if not SqlDb.is_connected():
            logger.info("Connecting to the SQL database...")
            SqlDb.connect("control_flow_fuzzer")
            logger.debug("SQL database connected.")
        logger.info("Clearing the SQL database...")
        SqlDb.execute("TRUNCATE fuzzed_of_message")
        SqlDb.execute("TRUNCATE log_error")
        SqlDb.commit()
        logger.debug("SQL database has been cleaned.")
        database_is_init = True
    finally:
        SqlDb.disconnect()
        if database_is_init is False:
            logger.error("An issue happened while initializing the database.")
            return False
        else:
            return True
# End def initialize


def before_each():
    """Job before after each test."""

    success = True

    # Flush the logs of ONOS
    success &= RyuDriver.flush_logs()

    # Stop running instances of onos
    success &= RyuDriver.stop()

    # Start onos
    success &= RyuDriver.start('ryu.app.simple_switch_14')

    return success
# End def before_each


def after_each():
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

    RyuDriver.stop()
    logger.debug("done")
# End def after_each


def terminate():
    """Job to be executed after the end of a series of test"""
    pass
# End def terminate


# ===== ( Main test function ) =========================================================================================


def test(instruction=None, retries=1):
    """
    Run the experiment
    :param instruction:
    :return:
    """

    # Write the instruction to the fuzzer
    logger.debug("Writing fuzzer instructions")
    if instruction is not None:
        FuzzerDriver.set_instructions(instruction)

    # Get the initial count of the database to be sure that a new data point is generated
    initial_db_count = count_db_entries()
    logger.debug("Initial database count = {}".format(initial_db_count))

    # Run the actual test function
    run_fuzz_test()

    # Verify that a new datapoint has been added
    db_count = count_db_entries()

    logger.debug("Database count delta = {}".format(db_count - initial_db_count))
    retry_cnt = 0
    datapoint_missing = (db_count - initial_db_count) < 1
    while datapoint_missing is True and retry_cnt < retries:
        logger.warning("Missing log entry for the experiment. Retrying ({}/{})".format(retry_cnt+1, retries))
        run_fuzz_test()

        # Count the datapoints
        db_count = count_db_entries()
        datapoint_missing = (db_count - initial_db_count) < 1
        # Increase the retry counter
        retry_cnt += 1

    if datapoint_missing:
        logger.error("Couldn't acquire the missing datapoint")
        return False
    else:
        return True
# End def test


# ===== ( Test sub-function ) ==========================================================================================

def run_fuzz_test():
    """Function that runs the actual test"""

    logger.info("Closing all previous instances on control flow fuzzer")
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
    time.sleep(5)

    # Check if mininet crashed
    alive, return_code = MininetDriver.is_alive()
    if alive is not True and return_code not in (None, ExitCode.EX_OK):
        logger.info("Mininet has crashed at {}".format(datetime.now()))
        logger.info("Saving status to the log message database")
        if not SqlDb.is_connected():
            SqlDb.connect('control_flow_fuzzer')

        try:
            # Storing a new log message stating that onos crashed
            level = "error"
            message = "*** Mininet has crashed (exit code: {}) ***".format(return_code)
            SqlDb.execute("INSERT INTO log_error (date, level, message) VALUES (NOW(6), %s, %s)", (level, message))
            SqlDb.commit()

        except Exception:
            logger.exception("An exception happened while recording mininet crash:")

        finally:
            SqlDb.disconnect()
# End def run_fuzz_test


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
