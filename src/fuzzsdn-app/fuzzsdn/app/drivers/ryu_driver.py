#!/usr/bin/env python3
import logging
import os.path
import subprocess
import time
from pathlib import Path

from fuzzsdn.app import setup


class RyuDriver:
    """
    Driver for Ryu SDN Controller.
    """

    __log = logging.getLogger(__name__)
    __handle        = None
    __ryu_proc      = None
    __log_dir       = None
    __log_file      = None
    __save_log      = False
    __start_time    = None

    # ===== Start Stop methods =========================================================================================

    @classmethod
    def start(cls, app_name, persist=False, save_log=True):
        """

        :param app_name: Name of the application to start Ryu with
        :param persist: If set to True, untie RYU from the
        :param save_log:
        :return:
        """

        # Get log directory
        cls.__log_dir = os.path.expanduser(setup.config().ryu.log_dir)

        if cls.__ryu_proc is not None:
            cls.__ryu_proc.terminate()
            cls.__ryu_proc = None

        if save_log is True:
            cls.__save_log  = True
            cls.__log_file  = os.path.join(cls.__log_dir, 'ryu.log')
            if not os.path.exists(cls.__log_dir):
                Path(cls.__log_dir).mkdir(parents=True, exist_ok=True)
            if os.path.exists(cls.__log_file):
                os.remove(cls.__log_file)
                if os.path.exists(cls.__log_file):
                    raise RuntimeError("Couldn't delete ryu log file \"{}\"".format(cls.__log_file))
        else:
            cls.__save_log  = False

        cls.__log.info("Starting RYU...")

        level_d = {
            'DEBUG'     : logging.DEBUG,
            'INFO'      : logging.INFO,
            'WARN'      : logging.WARNING,
            'ERROR'     : logging.ERROR,
            'CRITICAL'  : logging.CRITICAL
        }
        default_log_level = int(level_d.get(setup.config().ryu.log_level, logging.DEBUG))
        # Launch Ryu
        if cls.__save_log:
            cmd = ('ryu-manager',
                   '--default-log-level={}'.format(default_log_level),
                   '--log-file={}'.format(cls.__log_file),
                   '--ofp-tcp-listen-port={}'.format(setup.config().ryu.port),
                   '--verbose',
                   app_name)
        else:
            cmd = ('ryu-manager',
                   '--default-log-level={}'.format(default_log_level),
                   '--ofp-tcp-listen-port={}'.format(setup.config().ryu.port),
                   '--verbose',
                   app_name)

        cls.__log.trace("Executing command: {}".format(" ".join(cmd)))
        cls.__ryu_proc = subprocess.Popen(cmd,
                                          shell=False,
                                          preexec_fn=os.setsid() if persist is True else None,
                                          stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL
                                          )
        time.sleep(3)  # Necessary
        cls.__log.debug("Started ryu-manager.")
        return cls.__ryu_proc is not None
    # End def start

    @classmethod
    def stop(cls):
        if cls.__ryu_proc is not None:
            cls.__ryu_proc.terminate()
            subprocess.Popen.wait(cls.__ryu_proc)

        if cls.__save_log is True:
            # save the logs
            pass

        return True
    # End def stop

    @classmethod
    def flush_logs(cls):
        """Flush the log file generated by ONOS."""
        cls.__log.info("Flushing RYU logs...")
        try:
            dir_list = os.listdir(cls.__log_dir)
        except FileNotFoundError:
            # If there is no log directory, it may be because onos hasn't been started yet...
            # check if there is a root directory for onos
            if not os.path.isdir(cls.__log_dir):
                cls.__log.error("Couldn't flush RYU' logs: \"{}\" not found".format(cls.__log_dir))
                return False
        else:
            for item in dir_list:
                if item.startswith("ryu") and item.endswith(".log"):
                    path = os.path.join(cls.__log_dir, item)
                    cls.__log.debug("Flushing RYU log at \"{}\"".format(path))
                    os.remove(path)

        cls.__log.info("RYU logs have been flushed.")
        return True
    # End def flush_logs

# End class OnosDriver
