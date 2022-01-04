#!/usr/bin/env python3
import logging
import os.path
import subprocess
from time import sleep

import pexpect
from importlib import resources
import rdfl_exp.resources.tools.onos as onos_tools

ONOS_ROOT   = '/opt/onos/'
ONOS_BIN    = os.path.join(ONOS_ROOT, 'bin')
ONOS_KARAF  = os.path.join(ONOS_ROOT, 'karaf')
ONOS_LOG    = os.path.join(ONOS_KARAF, 'data', 'log')
KARAF_PWD   = 'karaf'
TIMEOUT     = 5


class OnosDriver:

    __log = logging.getLogger(__name__)

    # ===== Install Uninstall ==========================================================================================

    @classmethod
    def install(cls, force=True):
        """
        """
        with resources.path(onos_tools, "onos-install") as path:
            install_exe = path

        cls.__log.info("Installing ONOS...")
        try:
            if force is True:
                child = pexpect.spawn("{} --no-start --force --initd".format(install_exe))
            else:
                child = pexpect.spawn("{} --no-start --initd".format(install_exe))

            # NOTE: this timeout may need to change depending on the network
            # and size of ONOS
            index = child.expect([r"ONOS\sis\salready\sinstalled",
                                  r"Failed\sto\sstart",
                                  r"ONOS\sis\sinstalled",
                                  pexpect.TIMEOUT],
                                 timeout=180)
            if index == 0:
                # Process started
                # main.log.info("ONOS was installed on and started")
                # self.handle.expect(self.prompt)
                cls.__log.info("ONOS is already installed")
                return True
            elif index == 1:
                cls.__log.error("ONOS service failed to start")
                return False
            elif index == 2:
                cls.__log.info("ONOS has been installed.")
                return True
            elif index == 3:
                cls.__log.error("ONOS installation timed out")
                child.sendline("\x03")  # Control-C
                return False

        except pexpect.EOF:
            cls.__log.exception("ONOS installing threw an EOF exception")
            return False

        except Exception:
            cls.__log.exception("Uncaught Exception while installing ONOS")
            return False
    # End def install

    @classmethod
    def uninstall(cls):
        """
        """
        with resources.path(onos_tools, "onos-uninstall") as path:
            uninstall_exe = path
        try:
            # uninstall script does not return any output
            pexpect.run(uninstall_exe)
        except pexpect.TIMEOUT:
            return False
        except pexpect.EOF:
            return False
        except Exception:
            return False
        return True
    # End def uninstall

    @classmethod
    def start(cls):
        """
        Start an onos application
        :return:
        """
        # Call onos service
        cls.__log.info("Starting ONOS...")
        subprocess.call(["systemctl", "start", "onos"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

        start_level = False
        app_manager = False

        it = 0
        while start_level is False and it < 90:

            # connect to the ssh
            session = pexpect.spawn("ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "
                                    + "-p 8101 "
                                    + "karaf@localhost ")

            resp = session.expect(['Password:', pexpect.EOF, pexpect.TIMEOUT], timeout=TIMEOUT)
            if resp == 0:
                session.sendline(KARAF_PWD)
                session.expect('.*>.*', timeout=TIMEOUT)
                session.sendline("bundle:list | grep 'START LEVEL 100'")
                resp = session.expect(['START LEVEL 100', pexpect.EOF, pexpect.TIMEOUT], timeout=TIMEOUT)
                if resp == 0:
                    start_level = True
            else:
                session.close()

            it += 1

        cls.__log.debug("ONOS Start up: start level 100 reached?: {}".format(start_level))

        if start_level is True:
            it = 0
            while app_manager is False and it < 30 :

                cmd = "grep -E \"ApplicationManager .* Started\" {}/karaf.log".format(ONOS_LOG)
                session = pexpect.spawn(cmd)
                log_file = open("/home/ubuntu/karaf_log", "wb")
                session.logfile_read = log_file

                resp = session.expect(['Started', pexpect.EOF, pexpect.TIMEOUT], timeout=TIMEOUT)
                if resp == 0:
                    app_manager = True
                else:
                    sleep(1)

                it += 1
        cls.__log.debug("ONOS Start up: app manager started?: {}".format(app_manager))

        if app_manager is True and start_level is True:
            cls.__log.debug("ONOS has started.")
            return True
        else:
            cls.__log.error("ONOS did not start (start level 100: {}, app manager: {})".format(start_level, app_manager))
            return False
    # End def start

    @classmethod
    def stop(cls):
        cls.__log.info("Stopping ONOS...")
        subprocess.call(["systemctl", "stop", "onos"],
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL)

        it = 0
        stopped = False
        while stopped is False and it < 15:
            cmd = r"ps -ef | egrep \'java .*/onos/.* org\.apache\.karaf\.main\.Main\'"
            session = pexpect.spawn(cmd)

            resp = session.expect(['Started', pexpect.EOF, pexpect.TIMEOUT], timeout=TIMEOUT)
            if resp == 0:
                sleep(1)
            else:
                stopped = True

        if stopped is True:
            cls.__log.debug("ONOS has stopped.")
            return True
        else:
            cls.__log.error("ONOS did not stop properly.")
            return False
    # End def stop

    @classmethod
    def activate_app(cls, app_name: str, max_try=15):
        """
        Deactivate the an ONOS Application
        :param app_name: Name of the application to activate
        :param max_try: Number of attempts to activate the app
        :return: True if the app could be activated after x attempts, else return False
        """

        activated = False
        attempt = 0
        while activated is False and attempt < max_try:
            cls.__log.info("Activating ONOS app \"{}\"... Attempt {}/{}".format(app_name, attempt + 1, max_try))
            try:
                cmd = " ".join((os.path.join(ONOS_BIN, 'onos-app'), "localhost", "activate", app_name))
                child = pexpect.spawn(cmd)
            except Exception as e:
                return False, str(e)

            i = child.expect(['ACTIVE',
                              '404 Not Found',
                              pexpect.EOF,
                              pexpect.TIMEOUT],
                             TIMEOUT)

            if i == 0:
                activated = True
            elif i == 1:
                cls.__log.warning("Couldn't find ONOS app \"{}\".".format(app_name))
            else:
                cls.__log.warning("Failed to activate ONOS app \"{}\".".format(app_name))

            sleep(1)
            attempt += 1

        if activated is True:
            cls.__log.info("ONOS app \"{}\" is activated (took {} out of {} attempt(s)).".format(app_name, attempt, max_try))
        else:
            cls.__log.error("ONOS app \"{}\" couldn't be activated.")

        return activated
    # End def activate_app

    @classmethod
    def deactivate_app(cls, app_name: str):
        """
        Deactivate the an ONOS Application
        :param app_name: name of the application to activate
        :return: True (Always)
        """
        cls.__log.info("Deactivating ONOS app \"{}\"...".format(app_name))
        subprocess.call(["/opt/onos/bin/onos-app", "localhost", "deactivate", app_name],
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL)
        cls.__log.info("ONOS app \"{}\" is deactivated.".format(app_name))
        return True  # onos-app never an error message on that
    # End def deactivate_app

    @classmethod
    def flush_logs(cls):
        """Flush the log file generated by ONOS."""
        cls.__log.info("Flushing ONOS logs...")

        try:
            dir_list = os.listdir(ONOS_LOG)

        except FileNotFoundError:
            # If there is no log directory, it may be because onos hasn't been started yet...
            # check if there is a root directory for onos
            if not os.path.isdir(ONOS_ROOT) and not os.path.isdir(ONOS_KARAF):
                cls.__log.error("Couldn't flush ONOS' logs: ONOS or Karaf may not be installed.")
                return False
        else:
            for item in dir_list:
                if item.startswith("karaf") and item.endswith(".log"):
                    path = os.path.join(ONOS_LOG, item)
                    cls.__log.debug("Flushing ONOS log at \"{}\"".format(path))
                    os.remove(path)

        cls.__log.info("ONOS logs have been flushed.")
        return True
    # End def flush_onos_logs

# End class OnosDriver
