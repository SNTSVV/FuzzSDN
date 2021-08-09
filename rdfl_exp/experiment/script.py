#!/usr/bin/env python3
# coding: utf-8
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
from mininet.util import dumpNodeConnections

from rdfl_exp.utils.database import Database as SqlDb
from rdfl_exp.utils.terminal import progress_bar

REMOTE_CONTROLLER_IP = "10.240.5.104"

SQL_DB_ADDRESS = "10.240.5.104"
SQL_DB_USER = "dev"
SQL_DB_PASSWORD = "b14724x"

CFF_CFG_FOLDER = "/etc/packetfuzzer/"
CFF_USR_RULES_FILE = "fuzzer_instr.json"
CFF_PATH = "/home/ubuntu/cff/out/artifacts/PacketFuzzer_jar/PacketFuzzer.jar"
ONOS_LOG_DIR_PATH = "/opt/onos/karaf/data/log/"
CONTROL_FLOW_FUZZER_PORT = 52525

log = logging.getLogger("ExperimentScript")


# ===== ( Utility Functions ) ==================================================

def flush_onos_logs():
    dir_list = os.listdir(ONOS_LOG_DIR_PATH)
    for item in dir_list:
        if item.startswith("karaf") and item.endswith(".log"):
            path = os.path.join(ONOS_LOG_DIR_PATH, item)
            log.info("Flushing ONOS log at {}".format(path))
            os.remove(path)


# End def flush_onos_logs


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
    log.info("Writing instructions {} to {}".format(instructions, fuzz_instr_path))
    with open(fuzz_instr_path, 'w') as rf:
        rf.write(instructions)


# End def write_usr_rules


# ===== ( Main Function ) ======================================================

def run(count=1, instructions=None, clear_db: bool = False, print_progress_bar=False):
    """
    Run the experiment
    :param count:
    :param instructions:
    :param clear_db: Clear the database if set to True
    :return:
    """

    # ===== ( Setup Phase ) ====================================================

    intro_str = "Running the experiment script for {} iterations.".format(count)
    print(intro_str)
    log.info(intro_str)

    # Set mininet log level to INFO
    setLogLevel('warning')

    # Write the user rules
    if instructions is not None:
        write_usr_instr(instructions)

    # Connect to the database
    if not SqlDb.is_init():
        log.info("Initializing the SQL database")
        SqlDb.init(SQL_DB_ADDRESS, SQL_DB_USER, SQL_DB_PASSWORD)
        log.debug("Done")

    if clear_db:
        try:
            if not SqlDb.is_connected():
                log.info("Connecting to the SQL database")
                SqlDb.connect("control_flow_fuzzer")
                log.debug("Done")
            log.info("Clearing the SQL database")
            SqlDb.execute("TRUNCATE fuzzed_of_message")
            SqlDb.execute("TRUNCATE log_error")
            SqlDb.commit()
            log.debug("Done")
        finally:
            SqlDb.disconnect()

    # Stop running instances of onos
    log.info("Stopping running instances of ONOS")
    subprocess.call(["systemctl", "stop", "onos"],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL)
    log.debug("done")

    # ===== ( Experiment Phase ) ===============================================

    # Display the progress bar
    if print_progress_bar is True:
        progress_bar(0, count,
                     prefix='Progress:',
                     suffix='Complete ({}/{})'.format(0, count),
                     length=100)

    for it in range(count):
        log.info("Running iteration {}/{}".format(it + 1, count))

        start_timestamp = time.time()

        log.info("Flushing ONOS log files")
        flush_onos_logs()

        log.info("Starting ONOS")
        subprocess.call(["systemctl", "start", "onos"],
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL)
        time.sleep(5)  # Wait 10 sec to be sure

        log.info("Closing all previous instances on control flow fuzzer")
        for pid in get_pid("PacketFuzzer.jar"):
            os.kill(pid, signal.SIGKILL)

        log.info("Starting Control Flow Fuzzer")
        cff_process = subprocess.Popen(["java", "-jar", CFF_PATH],
                                       stderr=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL)

        log.info("Starting Mininet network")
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

        log.info("Executing ping command: h1 -> h2")
        exc_trace = h1.cmd("ping -c 1 {}".format(h2.IP()))
        log.debug("ping trace:\n{}".format(exc_trace))

        # Waiting for 2 seconds after ping
        time.sleep(2)

        # Check if mininet crashed
        mininet_pid = list(get_pid("mininet"))
        if len(mininet_pid) == 0:  # if 0 (active), print "Active"
            log.info("Mininet has crashed at {}".format(datetime.now()))
            log.info("Saving status to the log message database")
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
                log.exception("An exception happened while recording mininet crash:")

            finally:
                SqlDb.disconnect()
        else:
            log.info("Stopping the mininet network")
            net.stop()
            time.sleep(1)

        # Clean mininet
        log.info("Cleaning mininet")
        subprocess.call(["sudo", "mn", "-c"],
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL)
        log.debug("Done")

        log.info("Stopping Control Flow Fuzzer")
        cff_process.terminate()
        log.debug("Done")

        # Check if onos crashed
        onos_status = subprocess.call(
            ["systemctl", "is-active", "--quiet", "onos"])
        if onos_status != 0:  # if 0 (active), print "Active"
            log.info("*** Onos has crashed at {}".format(datetime.now()))
            log.info("*** Saving status to the log message database")
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
                log.exception("An exception happened while recording onos crash:")

            finally:
                SqlDb.disconnect()

        else:
            log.info("Stopping ONOS.")
            subprocess.call(["systemctl", "stop", "onos"],
                            stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL)

        log.info("Experiment duration: {}s".format(time.time() - start_timestamp))

        # Update the progress bar
        if print_progress_bar is True:
            progress_bar(it+1,
                         count,
                         prefix='Progress:',
                         suffix='Complete ({}/{})'.format(it+1, count),
                         length=100)
# End def run


# ===== ( Leftover ) ===========================================================

def simple_test():
    # Create and test a simple network
    topology = SingleTopo()
    network = Mininet(topo=topology,
                      controller=None)

    network.addController("c0",
                          controller=RemoteController,
                          ip=REMOTE_CONTROLLER_IP,
                          port=6653)
    network.start()

    print("Dumping host connections")
    dumpNodeConnections(network.hosts)

    print("Testing network connectivity")
    network.pingAll()

    network.stop()


# End def simple_test


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
