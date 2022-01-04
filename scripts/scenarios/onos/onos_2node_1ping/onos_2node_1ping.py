#!/usr/bin/env python3
# coding: utf-8
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import Host, OVSKernelSwitch, RemoteController
from mininet.topo import Topo

from drivers.onos_driver import OnosDriver
from rdfl_exp.utils.database import Database as SqlDb
from rdfl_exp.utils.log import LogPipe

# ===== ( Parameters ) =================================================================================================

REMOTE_CONTROLLER_IP        = "10.240.5.110"

SQL_DB_ADDRESS              = "10.240.5.110"
SQL_DB_USER                 = "dev"
SQL_DB_PASSWORD             = "b14724x"

CFF_CFG_FOLDER              = "/etc/packetfuzzer/"
CFF_USR_RULES_FILE          = "fuzzer_instr.json"
CFF_PATH                    = "/home/ubuntu/cff/out/artifacts/PacketFuzzer_jar/PacketFuzzer.jar"
ONOS_ROOT                   = "/opt/onos/"
ONOS_KARAF_ROOT             = os.path.join(ONOS_ROOT, 'karaf')
ONOS_LOG_DIR_PATH           = os.path.join(ONOS_KARAF_ROOT, 'log')
CONTROL_FLOW_FUZZER_PORT    = 52525

logger                      = logging.getLogger(__name__)
exp_logger                  = logging.getLogger("PacketFuzzer.jar")


# ===== ( Mininet Topology ) ===========================================================================================

class SingleTopo(Topo):
    # Single switch connected to n hosts
    def __init__(self, **opts):
        # Initialize topology and default option
        Topo.__init__(self, **opts)
        switches = []
        hosts = []

        # create switches
        switches.append(
            self.addSwitch('s1', cls=OVSKernelSwitch, protocols='OpenFlow14'))

        # create hosts
        hosts.append(
            self.addHost('h1', cls=Host, ip='10.0.0.1', defaultRoute=None))
        hosts.append(
            self.addHost('h2', cls=Host, ip='10.0.0.2', defaultRoute=None))

        self.addLink(hosts[0], switches[0])
        self.addLink(hosts[1], switches[0])
# End class SingleTopo

# ===== (Before, after functions) ======================================================================================


def initialize():
    """Job to be executed before the beginning of a series of test"""

    # Install onos
    logger.info("Installing ONOS...")
    installed = OnosDriver.install()
    if installed is not True:
        logger.error("Couldn't install ONOS")
        return False
    else:
        logger.debug("ONOS has been successfully installed.")

    # Connect to the database
    database_is_init = False
    if not SqlDb.is_init():
        logger.info("Initializing the SQL database...")
        SqlDb.init(SQL_DB_ADDRESS, SQL_DB_USER, SQL_DB_PASSWORD)
        logger.debug("The SQL database has been intialized successfully")

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
    success &= OnosDriver.flush_logs()

    # Set mininet log level to WARNING
    setLogLevel('warning')

    # Stop running instances of onos
    success &= OnosDriver.stop()

    # Start onos
    success &= OnosDriver.start()
    success &= OnosDriver.activate_app("org.onosproject.fwd")

    return success
# End def before_each


def after_each():
    """Job executed after each test."""

    if SqlDb.is_connected():
        logger.info("Disconnecting from the database...")
        SqlDb.disconnect()
        logger.info("Database is disconnected")

    OnosDriver.stop()
    logger.debug("done")
# End def after_each


def terminate():
    """Job to be executed after the end of a series of test"""
    OnosDriver.uninstall()
# End def terminate


# ===== ( Main test function ) =========================================================================================


def test(instruction=None, retries=1):
    """
    Run the experiment
    :param instruction:
    :return:
    """

    # Write the instruction to the fuzzer
    fuzz_instr_path = os.path.join(CFF_CFG_FOLDER, CFF_USR_RULES_FILE)
    logger.info("Writing instructions to {}".format(fuzz_instr_path))
    logger.debug("Instruction to write:\n{}".format(json.dumps(instruction, sort_keys=False, indent=4)))

    with open(fuzz_instr_path, 'w') as rf:
        rf.write(instruction)

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
    exp_stderr_pipe = LogPipe(logging.ERROR, "PacketFuzzer.jar")
    exp_stdout_pipe = LogPipe(logging.DEBUG, "PacketFuzzer.jar")
    cff_process = subprocess.Popen(["java", "-jar", CFF_PATH],
                                   stderr=exp_stderr_pipe,
                                   stdout=exp_stdout_pipe)

    time.sleep(2)  # Wait 2 sec to be sure

    logger.info("Starting Mininet network")
    topo = SingleTopo()
    net = Mininet(topo=topo,
                  controller=None)

    net.addController("c0",
                      controller=RemoteController,
                      ip=REMOTE_CONTROLLER_IP,
                      port=CONTROL_FLOW_FUZZER_PORT)

    net.start()
    time.sleep(5)  # Wait 5 secs

    h1, h2 = net.get('h1', 'h2')

    logger.info("Executing ping command: h1 -> h2")
    exc_trace = h1.cmd("ping -c 1 {}".format(h2.IP()))
    logger.trace("ping trace:\n{}".format(exc_trace))

    # Waiting for 2 seconds after ping
    time.sleep(2)

    # Check if mininet crashed
    mininet_pid = list(get_pid("mininet"))
    if len(mininet_pid) == 0:  # if 0 (active), print "Active"
        logger.info("Mininet has crashed at {}".format(datetime.now()))
        logger.info("Saving status to the log message database")
        if not SqlDb.is_connected():
            SqlDb.connect('control_flow_fuzzer')

        try:
            # Storing a new log message stating that onos crashed
            level = "error"
            message = "*** Mininet has crashed ***"
            SqlDb.execute(
                "INSERT INTO log_error (date, level, message) VALUES (NOW(6), %s, %s)",
                (level, message))
            SqlDb.commit()

        except (Exception,):
            logger.exception("An exception happened while recording mininet crash:")

        finally:
            SqlDb.disconnect()
    else:
        logger.info("Stopping the mininet network")
        net.stop()
        time.sleep(1)

    # Clean mininet
    logger.info("Cleaning mininet")
    subprocess.call(["sudo", "mn", "-c"],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL)
    logger.debug("Done")

    logger.info("Stopping Control Flow Fuzzer")
    exp_stderr_pipe.close()
    exp_stdout_pipe.close()
    cff_process.terminate()
    logger.debug("Done")

    # Check if onos crashed
    onos_status = subprocess.call(["systemctl", "is-active", "--quiet", "onos"])
    if onos_status != 0:  # if 0 (active), print "Active"
        logger.info("*** Onos has crashed at {}".format(datetime.now()))
        logger.info("*** Saving status to the log message database")
        if not SqlDb.is_connected():
            SqlDb.connect('control_flow_fuzzer')

        try:
            # Storing a new log message stating that onos crashed
            level = "error"
            message = "*** Onos has crashed ***"
            SqlDb.execute(
                "INSERT INTO log_error (date, level, message) VALUES (NOW(6), %s, %s)",
                (level, message))
            SqlDb.commit()

        except (Exception,):
            logger.exception("An exception happened while recording onos crash:")
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


def write_usr_instr(instructions: str):
    """Write the usr rules for the fuzzer."""
    fuzz_instr_path = os.path.join(CFF_CFG_FOLDER, CFF_USR_RULES_FILE)
    logger.info("Writing instructions to {}".format(fuzz_instr_path))
    logger.debug("Instruction to write:\n{}".format(json.dumps(instructions, sort_keys=False, indent=4)))

    with open(fuzz_instr_path, 'w') as rf:
        rf.write(instructions)
# End def write_usr_rules



