#!/usr/bin/env python3

import logging
import time
from typing import Optional, Tuple

import pexpect

from rdfl_exp.analytics.ping_stats import PingStats


from rdfl_exp.utils.exit_codes import ExitCode

SUDO_PWD = 'ubuntu'  # FIXME automatically find sudo pwd
MININET_PROMPT = "mininet>"


class MininetDriver:
    """
    MininetDriver is the basic driver which handles the Mininet functions
    """

    __log = logging.getLogger(__name__)
    __handle: Optional[pexpect.spawn] = None

    # ===== ( Start and Stop Mininet ) =================================================================================

    @classmethod
    def start(cls, topo_file=None, args=None, cmd=None, timeout=120):
        """
        Starts Mininet.

        Accepts a topology(.py) file and/or an optional argument, to start Mininet, as a parameter.
        Can also send regular mininet command to load up desired topology.
        Eg. Pass in a string 'mn --topo=tree,3,3' to mnCmd

        :param topo_file:   file path to a topology file (.py) (default to None)
        :param args:        Extra option added when starting the topology from the file
        :param cmd:         Mininet command use to start topology
        :param timeout:     Timeout in seconds for which we should wait for Mininet to connect

        :return: True if Mininet has started successfully, False otherwise.
        """
        try:
            alive, return_code = cls.is_alive()

            if alive is False:
                if return_code is not None:
                    cls.__handle = None

                # Clean up old networks
                cls.__log.info("Clearing any residual state or processes")
                cmd_ = "sudo mn -c"

                child = pexpect.spawn(cmd_)
                index = child.expect([r'password\sfor\s',
                                      r'Cleanup\scomplete',
                                      pexpect.EOF,
                                      pexpect.TIMEOUT],
                                     timeout)

                if index == 0:
                    # Sudo asking for password
                    cls.__log.info("Sending sudo password")
                    child.sendline(SUDO_PWD)
                    # add 1 to the index so it matches the previous one
                    index = 1 + child.expect([r'Cleanup\scomplete',
                                              pexpect.EOF,
                                              pexpect.TIMEOUT],
                                             timeout)

                if index == 1:
                    cls.__log.info("Cleanup is complete")
                elif index == 2:
                    cls.__log.error("Connection is terminated")
                elif index == 3:  # timeout
                    cls.__log.error("Something while cleaning Mininet took too long... ")
                    return False

                # Craft the string to start mininet
                cmd_ = []

                if cmd is None or cmd == '':
                    # If no file is given
                    if topo_file is None or topo_file == '':
                        cls.__log.info("Building Mininet from scratch")
                        cmd_.append("sudo mn")
                        if args is None or args == '':
                            pass
                        else:  # only use given args
                            # QUESTION: allow use of topo args and method args?
                            pass

                    # If no file is given
                    else:  # Use given topology file
                        cls.__log.info("Building Mininet with topology file \"{}\"".format(topo_file))
                        cmd_.append("python")
                        cmd_.append(topo_file)
                        if args is None or args == '':
                            pass
                    cmd_ = " ".join(cmd_)
                else:
                    if type(cmd) in (tuple, list):
                        cmd_ = " ".join(cmd)
                    elif type(cmd) == str:
                        cmd_ = cmd
                    else:
                        raise AttributeError("Wrong argument type \"cmd\" was given (got a: {}, expected a \"str\", a \"tuple\" or a \"list\")".format(type(cmd)))
                    cls.__log.info("Starting Mininet (with cmd: \"{}\")".format(cmd))

                # Send the command and check if network started
                cls.__log.info("Sending \"{}\" to Mininet CLI".format(cmd_))
                child = pexpect.spawn(cmd_)
                start_time = time.time()
                while True:
                    index = child.expect([MININET_PROMPT,
                                           r'Exception|Error',
                                           r'No\ssuch\sfile\sor\sdirectory',
                                           pexpect.EOF,
                                           pexpect.TIMEOUT],
                                          timeout)
                    if index == 0:
                        cls.__log.info("Mininet built. Time taken: {}".format(time.time() - start_time))
                        cls.__handle = child
                        return True
                    elif index == 1:
                        response = str(child.before + child.after)
                        print(response)
                        response += str(child.before + child.after)
                        cls.__log.error("Launching Mininet failed: {}".format(response))
                        return False

                    elif index == 2:
                        cls.__log.error(child.before + child.after)
                        print(index, "{}".format(child.before + child.after))
                        return False

                    elif index == 3:
                        cls.__log.error("Connection timeout")
                        print("Connection timeout")
                        print(child.before)
                        print(child.after)
                        return False

                    elif index == 4:  # timeout
                        cls.__log.error("Something took too long... ")
                        cls.__log.debug(child.before + child.after)
                        print("Something took too long...\n{}".format(child.before + child.after))
                        return False
            else:
                cls.warning("Trying to connect to Miniet while it's already connected")
                return True
        except pexpect.TIMEOUT:
            cls.__log.exception("TIMEOUT exception found while starting Mininet")
            cls.__log.error("   " + child.before)
            return False
        except pexpect.EOF:
            cls.__log.error("EOF exception found while starting Mininet")
            cls.__log.error("   " + child.before)
            return False
        except Exception:
            cls.__log.exception("Uncaught exception while starting Mininet")
            return False

    @classmethod
    def stop(cls, timeout=5, exit_timeout=1000):
        """
        Stops Mininet.
        
        :return: True if Mininet successfully stops or if the handle doesn't exists, False otherwise
        """
        response = ''
        if cls.__handle is not None:
            cls.__log.info("Stopping mininet...")
            try:
                cls.__handle.sendline("")
                i = cls.__handle.expect([MININET_PROMPT,
                                         pexpect.EOF,
                                         pexpect.TIMEOUT],
                                        timeout)

                # Mininet is still running
                if i == 0:
                    cls.__log.info("Exiting mininet..")
                    start_time = time.time()
                    cls.__handle.sendline("exit")
                    exit_return = 1
                    while exit_return:
                        exit_return = cls.__handle.expect([pexpect.EOF,
                                                           "Traceback",
                                                           "AssertionError",
                                                           MININET_PROMPT],
                                                          timeout=exit_timeout)

                    cls.__log.info("Mininet as stopped. Time taken: {}".format(time.time() - start_time))
                    cls.__handle.sendline("sudo mn -c")

                    cls.__handle.expect(pexpect.EOF)
                    cls.__handle = None
                    return True

                elif i == 1:
                    cls.__log.error("Something went wrong exiting mininet")
                    return False

                elif i == 2:  # timeout
                    cls.__log.error("Mininet TIMEOUT while exiting")
                    return False

            except pexpect.TIMEOUT:
                cls.__log.error("TIMEOUT exception found")
                cls.__log.error("    " + cls.__handle.before)
                return False
            except pexpect.EOF:
                cls.__log.error("EOF exception found")
                cls.__log.error("    " + cls.__handle.before)
                return False
            except Exception:
                cls.__log.exception("Uncaught exception!")
                return False
        else:
            cls.__log.warning("Mininet is not started")
            return True
    # End def stop

    @classmethod
    def is_alive(cls) -> Tuple[bool, Optional[ExitCode]]:
        if cls.__handle is not None:
            if cls.__handle.isalive():
                return True, None
            else:
                return False, ExitCode(cls.__handle.exitstatus) if ExitCode.has_value(cls.__handle.exitstatus) else ExitCode.UNDEF
        else:
            return False, None
    # End def is_alive

    # ===== ( Start and Stop Mininet ) =================================================================================

    @classmethod
    def ping_host(cls, src : str, dst : str, count : int = 1, wait_timeout : float = 1.0, interval : float = 1.0) -> Optional[PingStats]:
        """
        Ping from one mininet host to another

        :param src: the source host from which the ping should be sent from.
        :param dst: the destination host to which the ping should be sent.
        :param count: the number of ping message to send (default to 1).
        :param wait_timeout: the maximum time allowed (in seconds) between a ping and its response.
        :param interval: the interval (in seconds) between two ping messages

        :return: an instance of PingStats if the ping was successful, None otherwise
        """

        # Check if mininet is started
        if not cls.is_alive()[0]:
            cls.__log.warning("Mininet is not started. Cannot ping hosts.")
            return None

        # Build the ping command
        cmd = "{} ping {} -c {} -i {} -W {}".format(src, dst, count, interval, wait_timeout)
        
        try:
            cls.__log.info("Sending command \"{}\" to Mininet".format(cmd))
            cls.__handle.sendline(cmd)
            i = cls.__handle.expect([cmd, pexpect.TIMEOUT], timeout=(wait_timeout+interval)*count + 5)

            if i == 0:
                pass
            
            elif i == 1:
                cls.__log.error("Timed out when sending \"{}\" to Mininet".format(cmd))
                cls.__log.error("Response: {}".format(cls.__handle.before))
                return None
            
            i = cls.__handle.expect([MININET_PROMPT, pexpect.TIMEOUT])

            # Parse the ping results
            if i == 0:
                response = cls.__handle.before
                return PingStats(response.decode('utf-8'))
                
            elif i == 1:
                cls.__log.error("Timed out when for a response to \"{}\" from Mininet".format(cmd))
                cls.__log.error("Handle: {}".format(cls.__handle))
                return None
            
        except pexpect.EOF:
            cls.__log.error("Got an EOF exception when executing ping command \"{}\"".format(cmd))
            cls.__log.error("Handle before: {}".format(cls.__handle.before))
            return None

        except Exception:
            cls.__log.exception("Uncaught exception when executing ping command \"{}\" !".format(cmd))
            return None
    # End def ping_host

# End class MininetDriver
