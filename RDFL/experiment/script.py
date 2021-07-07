#!/usr/bin/python
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from random import randint

from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import Host, OVSKernelSwitch, RemoteController
from mininet.topo import Topo
from mininet.util import dumpNodeConnections
from utils.database import Database as SqlDb
from utils.terminal import Fore, Style

REMOTE_CONTROLLER_IP = "10.240.5.104"

SQL_DB_ADDRESS = "10.240.5.104"
SQL_DB_USER = "dev"
SQL_DB_PASSWORD = "b14724x"

CFF_CFG_FOLDER = "/etc/packetfuzzer/"
CFF_USR_RULES_FILE = "fuzzer_instr.json"
CFF_PATH = "/home/ubuntu/cff/out/artifacts/PacketFuzzer_jar/PacketFuzzer.jar"
ONOS_LOG_DIR_PATH = "/opt/onos/karaf/data/log/"
CONTROL_FLOW_FUZZER_PORT = 52525


# ===== ( Utility Functions ) ==================================================

def flush_onos_logs():
    dir_list = os.listdir(ONOS_LOG_DIR_PATH)
    for item in dir_list:
        if item.startswith("karaf") and item.endswith(".log"):
            path = os.path.join(ONOS_LOG_DIR_PATH, item)
            print("Removing {}".format(path))
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
    print("Writing instructions to {}".format(fuzz_instr_path))
    with open(fuzz_instr_path, 'w') as rf:
        rf.write(instructions)


# End def write_usr_rules


# ===== ( Main Function ) ======================================================

def run(count=1, instructions=None, clear_db: bool = False):
    """
    Run the experiment
    :param count:
    :param instructions:
    :param clear_db: Clear the database if set to True
    :return:
    """

    # ===== ( Setup Phase ) ====================================================

    # Set mininet log level to INFO
    setLogLevel('info')

    # Check that we have root permissions to run the program
    if os.geteuid() != 0:
        raise SystemExit(
            Fore.RED + Style.BOLD + "Error" + Style.RESET
            + ": This program must be run with root permissions."
            + " Try again using \"sudo\".")

    # Write the user rules
    if instructions is not None:
        write_usr_instr(instructions)

    # Connect to the database
    print("*** Connecting to the database")
    SqlDb.init(SQL_DB_ADDRESS, SQL_DB_USER, SQL_DB_PASSWORD)
    SqlDb.connect("control_flow_fuzzer")

    if clear_db:
        SqlDb.execute("DELETE FROM fuzzed_of_message")
        SqlDb.execute("DELETE FROM log_error")
        SqlDb.commit()

    # Stop running instances of onos
    print("*** Stopping running instances of ONOS")
    subprocess.call(["systemctl", "stop", "onos"],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL)
    time.sleep(1)  # Wait 1 sec to be sure

    # ===== ( Experiment Phase ) ===============================================

    for it in range(count):
        print("###### Iteration {}/{} ######".format(it + 1, count))

        start_timestamp = time.time()

        print("*** Flushing ONOS log files")
        flush_onos_logs()

        print("*** Starting ONOS")
        subprocess.call(["systemctl", "start", "onos"],
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL)
        time.sleep(5)  # Wait 10 sec to be sure

        print("Closing all previous instances on control flow fuzzer")
        for pid in get_pid("PacketFuzzer.jar"):
            os.kill(pid, signal.SIGKILL)

        print("*** Starting Control Flow Fuzzer")
        cff_process = subprocess.Popen(["java", "-jar", CFF_PATH],
                                       stderr=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL)

        print("*** Starting Mininet network")
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
        if randint(0, 1) == 0:
            print("*** Executing ping command: h1 -> h2")
            print(h1.cmd("ping -c 1 {}".format(h2.IP())))
        else:
            print("*** Executing ping command: h2 -> h1")
            print(h2.cmd("ping -c 1 {}".format(h1.IP())))

        # Waiting for 2 seconds after ping
        time.sleep(2)

        # Check if mininet crashed
        mininet_pid = list(get_pid("mininet"))
        if len(mininet_pid) == 0:  # if 0 (active), print "Active"
            print("*** Mininet has crashed at {}".format(datetime.now()))
            print("*** Saving status to the log message database")
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

            finally:
                SqlDb.disconnect()
        else:
            print("*** Stopping the mininet network")
            net.stop()

            print("wait for 1 sec")
            time.sleep(1)

        # Clean mininet
        subprocess.call(["sudo", "mn", "-c"],
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL)

        print("*** Stopping Control Flow Fuzzer")
        cff_process.terminate()
        time.sleep(1)  # Wait 1 sec to be sure

        # Check if onos crashed
        onos_status = subprocess.call(
            ["systemctl", "is-active", "--quiet", "onos"])
        if onos_status != 0:  # if 0 (active), print "Active"
            print("*** Onos has crashed at {}".format(datetime.now()))
            print("*** Saving status to the log message database")
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

            finally:
                SqlDb.disconnect()

        else:
            print("*** Stopping ONOS")
            subprocess.call(["systemctl", "stop", "onos"],
                            stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL)
            time.sleep(1)  # Wait 1 sec to be sure

        print("Experiment duration: {}s ".format(time.time() - start_timestamp))
        print("#########################################################")


# End def main


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
