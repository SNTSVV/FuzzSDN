#!/usr/bin/env python3
import logging
import os.path
import subprocess
from importlib import resources
from time import sleep

import pexpect

import figsdn.resources.tools.onos as onos_tools
from figsdn.app import setup
from figsdn.app.drivers.commons import sudo_expect


class OnosDriver:
    """
    Driver for ONOS SDN Controller.
    """
    __log = logging.getLogger(__name__)
    __timeout = 5

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
                child = pexpect.spawn("sudo {} --no-start --force --initd".format(install_exe))
            else:
                child = pexpect.spawn("sudo {} --no-start --initd".format(install_exe))

            # NOTE: this timeout may need to change depending on the network
            try:
                i = sudo_expect(spawn=child,
                                pattern=[r"ONOS\sis\salready\sinstalled",
                                         r"Failed\sto\sstart",
                                         r"ONOS\sis\sinstalled",
                                         pexpect.TIMEOUT],
                                timeout=180)
            except KeyError:
                cls.__log.error("Unable to stop ONOS due to permission issues. Is sudo configured?")
                cls.__log.error("Add figsdn to sudoers or configure sudo password in configuration file")
                return False

            if i == 0:
                # Process started
                # main.log.info("ONOS was installed on and started")
                # self.handle.expect(self.prompt)
                cls.__log.info("ONOS is already installed")
                return True
            elif i == 1:
                cls.__log.error("ONOS service failed to start")
                return False
            elif i == 2:
                cls.__log.info("ONOS has been installed.")
                return True
            elif i == 3:
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

    # ===== Start and Stop =============================================================================================

    @classmethod
    def start(cls):
        """
        Start an onos application
        :return:
        """
        # Call onos service
        cls.__log.info("Starting ONOS...")
        child = pexpect.spawn("sudo systemctl start onos")

        try:
            i = sudo_expect(spawn=child,
                            pattern=[pexpect.EOF],
                            timeout=180)
        except KeyError:
            cls.__log.error("Unable to start ONOS due to permission issues. Is sudo configured?")
            cls.__log.error("Add figsdn to sudoers or configure sudo password in configuration file")
            return False

        if i == 0:
            # QUESTION: Maybe we should check something here ?
            pass

        start_level = False
        app_manager = False

        it = 0
        while start_level is False and it < 90:

            # connect to the ssh
            session = pexpect.spawn("ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "
                                    + "-p 8101 "
                                    + "karaf@localhost ")

            resp = session.expect(['Password:', pexpect.EOF, pexpect.TIMEOUT], timeout=cls.__timeout)
            if resp == 0:
                session.sendline(setup.config().onos.karaf_password)
                resp = session.expect([r'.*>.*',
                                       r'Connection\sclosed\sby',
                                       pexpect.EOF,
                                       pexpect.TIMEOUT]
                                      , timeout=cls.__timeout)
                if resp == 0:
                    session.sendline("bundle:list | grep 'START LEVEL 100'")
                    resp = session.expect(['START LEVEL 100', pexpect.EOF, pexpect.TIMEOUT], timeout=cls.__timeout)
                    if resp == 0:
                        start_level = True
                elif resp == 1:
                    cls.__log.warning("Couldn't establish ssh session with karaf")

            session.close()
            it += 1

        cls.__log.debug("ONOS Start up: start level 100 reached?: {}".format(start_level))

        if start_level is True:
            it = 0
            while app_manager is False and it < 30 :

                cmd = "grep -E \"ApplicationManager .* Started\" {}".format(os.path.join(setup.config().onos.root_dir, 'karaf', 'data', 'log', "karaf.log"))
                session = pexpect.spawn(cmd)
                resp = session.expect(['Started', pexpect.EOF, pexpect.TIMEOUT], timeout=cls.__timeout)
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
        child = pexpect.spawn("sudo systemctl stop onos")

        try:
            i = sudo_expect(spawn=child, pattern=[pexpect.EOF], timeout=180)
        except KeyError:
            cls.__log.error("Unable to stop ONOS due to permission issues. Is sudo configured?")
            cls.__log.error("Add figsdn to sudoers or configure sudo password in configuration file")
            return False

        if i == 0:
            # QUESTION: Maybe we should check something here ?
            pass

        it = 0
        stopped = False
        while stopped is False and it < 100:
            cmd = r"ps -ef | egrep \'java .*/onos/.* org\.apache\.karaf\.main\.Main\'"
            session = pexpect.spawn(cmd)

            resp = session.expect(['Started', pexpect.EOF, pexpect.TIMEOUT], timeout=cls.__timeout)
            if resp == 0:
                sleep(0.1)
            else:
                stopped = True

        if stopped is True:
            cls.__log.debug("ONOS has stopped.")
            return True
        else:
            cls.__log.error("ONOS did not stop properly.")
            return False
    # End def stop

    # ===== App activation =============================================================================================

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
        cmd = " ".join((os.path.join(setup.config().onos.root_dir, 'bin', 'onos-app'), "localhost", "activate", app_name))
        while activated is False and attempt < max_try:
            cls.__log.info("Activating ONOS app \"{}\"... Attempt {}/{}".format(app_name, attempt + 1, max_try))
            try:
                child = pexpect.spawn(cmd)
            except Exception:
                cls.__log.exception("An exception happened while activating application {} (cmd: {})".format(app_name, cmd))
                return False

            i = child.expect(['ACTIVE',
                              '404 Not Found',
                              pexpect.EOF,
                              pexpect.TIMEOUT],
                             cls.__timeout)

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
            cls.__log.error("ONOS app \"{}\" couldn't be activated.".format(app_name))

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
        subprocess.call([os.path.join(setup.config().onos.root_dir, 'bin', 'onos-app'), "localhost", "deactivate", app_name],
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
            dir_list = os.listdir(os.path.join(setup.config().onos.root_dir, 'karaf', 'data', 'log'))
        except FileNotFoundError:
            # If there is no log directory, it may be because onos hasn't been started yet...
            # check if there is a root directory for onos
            if not os.path.isdir(setup.config().onos.root_dir) and not os.path.isdir(os.path.join(setup.config().onos.root_dir, 'karaf')):
                cls.__log.error("Couldn't flush ONOS' logs: ONOS or Karaf may not be installed.")
                return False
        else:
            for item in dir_list:
                if item.startswith("karaf") and item.endswith(".log"):
                    path = os.path.join(setup.config().onos.root_dir, 'karaf', 'data', 'log', item)
                    cls.__log.debug("Flushing ONOS log at \"{}\"".format(path))
                    try:
                        os.remove(path)
                    except PermissionError:
                        # It is highly probable that sudo is required to delete those files.
                        # If so, try again using sudo
                        child = pexpect.spawn("sudo rm {}".format(path))
                        try:
                            sudo_expect(spawn=child, pattern=[pexpect.EOF], timeout=180)
                        except KeyError:
                            cls.__log.error("Unable to remove ONOS log file \"{}\". Is sudo configured?".format(path))
                            cls.__log.error("Add figsdn to sudoers or configure sudo password in configuration file")
                            return False
                    finally:
                        cls.__log.trace("Removed \"{}\"".format(path))

        cls.__log.info("ONOS logs have been flushed.")
        return True
    # End def flush_onos_logs

    # ===== set log level ====

    @classmethod
    def set_log_level(cls, level : str):
        """Sets the log level of onos

        Args:
            level ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR') : The log level of to choose from.
        """
        allowed_levels = ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR')
        if level not in allowed_levels:
            raise AttributeError(
                "ONOS log level must be either {} or {}, not \"{}\"".format(", ".join(allowed_levels[:-1]),
                                                                            allowed_levels[-1], level))
        # connect to the ssh
        log_level_set = False
        session = pexpect.spawn("ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "
                                + "-p 8101 "
                                + "karaf@localhost ")
        try:
            resp = session.expect(['Password:', pexpect.EOF, pexpect.TIMEOUT], timeout=cls.__timeout)
            if resp == 0:
                session.sendline(setup.config().onos.karaf_password)
                resp = session.expect([r'.*>.*',
                                       r'Connection\sclosed\sby',
                                       pexpect.EOF,
                                       pexpect.TIMEOUT]
                                      , timeout=cls.__timeout)

                if resp == 0:
                    session.sendline("log:set {}".format(level))
                    resp = session.expect([r'.*>.*', pexpect.EOF, pexpect.TIMEOUT], timeout=cls.__timeout)
                    if resp == 0:
                        log_level_set = True  # all good
                    elif resp > 0:
                        cls.__log.warning("Something wrong happened while setting ONOS log level.")

                elif resp == 1:
                    cls.__log.warning("Couldn't establish ssh session with karaf")
        finally:
            session.close()
            return log_level_set
# End class OnosDriver
