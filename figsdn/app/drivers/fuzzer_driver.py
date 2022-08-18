#!/usr/bin/env python3
import json
import logging
import os
import subprocess
from time import sleep
from typing import Optional

import pexpect

from figsdn.app import setup
from figsdn.app.drivers.commons import sudo_expect
from figsdn.common import app_path
from figsdn.common.utils.log import LogPipe


class FuzzerDriver:
    """A class that handles all operations with the database."""

    __log = logging.getLogger(__name__)
    __handle : Optional[subprocess.Popen] = None
    __stderr_pipe = None
    __stdout_pipe = None

    @classmethod
    def set_instructions(cls, instructions: str):
        """Write the usr rules for the fuzzer."""
        instr_path = os.path.expanduser(setup.config().fuzzer.instr_path)

        cls.__log.info("Writing fuzzer instructions to {}".format(instr_path))
        cls.__log.debug("Instruction to write: {}".format(json.dumps(instructions)))

        with open(instr_path, 'w') as f:
            f.write(instructions)
    # End def set_fuzzer_instructions

    # ===== Start and Stop methods =====================================================================================

    @classmethod
    def start(cls):

        # Flush last fuzz report
        path = os.path.join(app_path.data_dir(), 'fuzz_report.json')  # TODO: Read that from fuzzer configuration file
        if os.path.exists(path):
            cls.__log.debug("Flushing Fuzzer report at \"{}\"".format(path))

            try:
                os.remove(path)
                cls.__log.trace("Removed \"{}\"".format(path))
            except PermissionError:
                # It is highly probable that sudo is required to delete those files.
                # If so, try again using sudo
                child = pexpect.spawn("sudo rm {}".format(path))
                try:
                    sudo_expect(spawn=child, pattern=[pexpect.EOF], timeout=180)
                    cls.__log.trace("Removed \"{}\"".format(path))
                except KeyError:
                    cls.__log.error("Unable to remove fuzz report \"{}\". Is sudo configured?".format(path))
                    cls.__log.error("Add figsdn to sudoers or configure sudo password in configuration file")

        # Start the fuzzer
        cls.__log.info("Starting Control Flow Fuzzer")

        cls.__stderr_pipe = LogPipe(logging.ERROR, __name__ + "PacketFuzzer.jar")
        cls.__stdout_pipe = LogPipe(logging.DEBUG, __name__ + "PacketFuzzer.jar")
        # noinspection PyTypeChecker
        cls.__handle = subprocess.Popen(
            ["java", "-jar", os.path.expanduser(setup.config().fuzzer.jar_path)],
            stderr=cls.__stderr_pipe,
            stdout=cls.__stdout_pipe
        )

        # TODO: Replace by a check, to know if the Fuzzer has properly started
        sleep(2)  # Wait 2 sec to be sure
        return True
    # End def start

    @classmethod
    def stop(cls, timeout: float = 5.0):
        if cls.__handle is not None:
            cls.__log.info("Stopping Control Flow Fuzzer")
            cls.__stdout_pipe.close()
            cls.__stderr_pipe.close()
            cls.__handle.terminate()
            # TODO: Make the fuzzer close properly
            # terminated = False
            #
            # t_end = datetime.now() + timedelta(seconds=timeout)
            # while terminated is not True and datetime.now() < t_end:
            #     terminated = cls.__handle.poll()
            # if terminated is not True:
            #     cls.__log.warning("Fuzzer has failed to terminate under {}s, force killing it".format(timeout))
            #     cls.__handle.kill()
            # cls.__handle = None

        return True
    # End def stop

# End def set_fuzzer_instructions
