#!/usr/bin/env python3
# coding: utf-8

import importlib.util
import json
import logging
import re
from enum import Enum
from importlib import resources
from timeit import default_timer as timer

from iteround import saferound

import rdfl_exp.resources.criteria
from rdfl_exp.machine_learning.rule import CTX_PKT_IN_tmp, convert_to_fuzzer_actions
from rdfl_exp.utils.terminal import progress_bar


class FuzzMode(Enum):
    UNDEFINED   = 0,
    RANDOM      = 1,
    RULE        = 2,
# End class FuzzMode


# TODO: set all the path from the main directory path automatically


class Experimenter:

    def __init__(self, safe_mode=True):

        self.log = logging.getLogger(__name__)
        self.safe_mode = safe_mode if isinstance(safe_mode, bool) else True

        self.scenario = None
        self.criterion = dict()

        # Fuzzing parameters
        self.fuzz_mode = FuzzMode.UNDEFINED
        self.rule_set = None
        self.enable_mutation = True
        self.mutation_rate = 1.0
    # End def __init__

    def set_scenario(self, name):
        """
        Set the scenario that should be used
        :param name: name of the scenario
        :return:
        """
        # Check if the scenario exists
        scenario_pkg = "rdfl_exp.resources.scenarios.{0}.{0}".format(name)
        try:
            self.scenario = importlib.import_module(scenario_pkg)
        except ModuleNotFoundError as e:
            self.log.error("Couldn't find scenario \"{}\".".format(name))
            if self.safe_mode is True:
                raise e
        except Exception as e:
            self.log.exception("Uncaught exception while importing scenario \"{}\"".format(name))
            raise e
        else:
            self.log.info("Loaded scenario {}".format(name))
    # End def set_experiment

    def set_fuzzing_mode(self, mode: FuzzMode):
        self.fuzz_mode = mode
        self.log.debug("Current fuzzing mode: {}".format(mode))
    # End def set_fuzzer_mode

    def set_rule_set(self, rule_set):
        self.rule_set = rule_set
    # End def set_rules

    def set_criterion(self, name: str, **kwargs):
        """
        :param name:
        :param kwargs:
        :return:
        """
        criterion_file_name = "{}.json".format(name)

        try:
            # Load the criteria
            criterion = resources.read_text(rdfl_exp.resources.criteria, criterion_file_name)

            # Replace the variables by arguments
            pattern = re.compile(r'(?<=\")(\$\w+)(?=\")')
            for _var in re.findall(pattern, criterion):
                _var_arg = _var.replace('$', '')
                if _var_arg in kwargs:
                    criterion = criterion.replace(_var, kwargs.get(_var_arg))
                else:
                    # TODO: Mayber raise and error instead ?
                    self.log.warning("No value defined to replace \"{}\" in criterion \"{}\"".format(_var, name))

            # Finally store the current criterion
            self.log.info("Loaded criterion \"{}\"".format(name))
            self.criterion = json.loads(criterion)

        except FileNotFoundError as e:
            self.log.error("Couldn't find criterion \"{}\".".format(name))
            if self.safe_mode is True:
                raise e
    # End def set_rule

    def run(self, count=1):
        """
        Main loop
        :param count:
        :return:
        """

        # ===== INITIALIZE ==============================================================================================
        # Before running a test, run the "initialize" function of the scenario
        if hasattr(self.scenario, "initialize") and hasattr(self.scenario.initialize, '__call__'):
            try:
                self.log.debug("Running \"{}#initialize\"".format(self.scenario.__name__))
                self.scenario.initialize()
            except Exception as e:
                if self.safe_mode is True:
                    self.log.exception(
                        "An exception occurred while running \"{}#initialize\"".format(self.scenario.__name__))
                    raise e
                else:
                    # TODO: issue a warning message to the log
                    pass
        elif self.safe_mode is True:
            self.log.error(
                "Function \"{}#initialize\" is not defined, or it is not a function".format(self.scenario.__name__))
            raise AttributeError(
                "Function \"{}#initialize\" is not defined, or it is not a function".format(self.scenario.__name__))
        else:
            self.log.warning(
                "Function \"{}#initialize\" is not defined, or it is not a function".format(self.scenario.__name__))

        # ===== MAIN TEST ==============================================================================================

        progress_bar(0, count, prefix='Progress:', suffix='Complete ({}/{})'.format(0, count), length=100)

        # Build the fuzzer instruction
        fuzz_instr = self.__build_fuzzer_instruction(count=count)

        for i in range(count):
            # Start a time
            start_time = timer()
            # ===== BEFORE EACH ========================================================================================

            # Try to run the 'before_each' function
            if hasattr(self.scenario, "before_each") and hasattr(self.scenario.before_each, '__call__'):
                try:
                    self.log.debug("Running \"{}#before_each\"".format(self.scenario.__name__))
                    self.scenario.before_each()
                except Exception as e:
                    if self.safe_mode is True:
                        self.log.exception(
                            "An exception occurred while running \"{}#before_each\"".format(self.scenario.__name__))
                        raise e
                    else:
                        # TODO: issue a warning message to the log
                        pass

            # Try to run the 'test' function
            if hasattr(self.scenario, "test") and hasattr(self.scenario.test, '__call__'):
                try:
                    self.log.debug("Running \"{}#test\"".format(self.scenario.__name__))
                    self.scenario.test(instruction=fuzz_instr[i], retries=5)
                except Exception as e:
                    if self.safe_mode is True:
                        self.log.exception(
                            "An exception occurred while running \"{}#test\"".format(self.scenario.__name__))
                        raise e
                    else:
                        # TODO: issue a warning message to the log
                        pass
            else:
                raise AttributeError("The function \"test\" is not defined in script {}".format(self.scenario.__name__))

            # Try to run the 'after_each' function
            if hasattr(self.scenario, "after_each") and hasattr(self.scenario.after_each, '__call__'):
                try:
                    self.log.debug("Running \"{}#after_each\"".format(self.scenario.__name__))
                    self.scenario.after_each()
                except Exception as e:
                    if self.safe_mode is True:
                        self.log.exception(
                            "An exception occurred while running \"{}#after_each\"".format(self.scenario.__name__))
                        raise e
                    else:
                        # TODO: issue a warning message to the log
                        pass
            stop_time = timer()
            self.log.info("Test {} out of {} of scenario \"{}\" has been completed in {}s.".format(i + 1,
                                                                                                   count,
                                                                                                   self.scenario.__name__,
                                                                                                   stop_time - start_time))
            progress_bar(i + 1, count, prefix='Progress:', suffix='Complete ({}/{})'.format(i + 1, count), length=100)

        # If it's the last experiment, run the function on_last_instance
        if hasattr(self.scenario, "terminate") and hasattr(self.scenario.terminate, '__call__'):
            try:
                self.log.debug("Running \"{}#terminate\"".format(self.scenario.__name__))
                self.scenario.terminate()
            except Exception as e:
                if self.safe_mode is True:
                    self.log.exception(
                        "An exception occurred while running \"{}#terminate\"".format(self.scenario.__name__))
                    raise e
                else:
                    # TODO: issue a warning message to the log
                    pass
    # End def run

    # ===== ( Private methods ) ========================================================================================

    def __build_fuzzer_instruction(self, count=1):
        """
        Build a fuzzer instruction depending on the fuzz mode
        :return: the fuzz action string
        """
        # Create an instruction list of "count" instructions
        instructions = list()

        # If we fuzz randomly, populate the instructions with a
        if self.fuzz_mode == FuzzMode.RANDOM:
            for i in range(count):
                # Create the dictionary
                json_dict = dict()
                json_dict.update(self.criterion)
                json_dict['actions'] = [{
                    "intent": "mutate_packet",
                    "includeHeader": False
                }]
                instructions.append(json.dumps({"instructions": [json_dict]}))

        # Else
        elif self.fuzz_mode == FuzzMode.RULE:
            # Create a list of actions
            fuzz_action = list()
            # Get the budget
            budget_list = self.__get_budget_for_rules(sample_size=count)

            for i in range(len(budget_list)):
                # Create the action for the rule i
                if budget_list[i] > 0:
                    actions = convert_to_fuzzer_actions(
                        rule=self.rule_set[i],
                        n=budget_list[i],
                        include_header=False,
                        enable_mutation=True,
                        mutation_rate=self.mutation_rate,
                        ctx=CTX_PKT_IN_tmp
                    )
                    for action in actions:
                        json_dict = dict()
                        json_dict.update(self.criterion)  # add the criterion
                        json_dict['actions'] = [action]
                        instructions.append(json.dumps({"instructions": [json_dict]}))  # add it to the instruction

        else:
            raise RuntimeError("Cannot build instructions for {}".format(self.fuzz_mode))
        return instructions
    # End def __build_fuzzer_action

    def __get_budget_for_rules(self, sample_size):
        rounded_budget = saferound(
            [self.rule_set.budget(i, method=0) * sample_size for i in range(len(self.rule_set))],
            places=0
        )
        return [int(x) for x in rounded_budget]
# End class Experimenter
