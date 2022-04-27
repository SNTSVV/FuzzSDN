#!/usr/bin/env python3
# coding: utf-8

import importlib.util
import json
import logging
import re
from enum import Enum
from importlib import resources
from timeit import default_timer as timer
from typing import Optional, Union, Tuple

from iteround import saferound

import rdfl_exp.resources.criteria
from rdfl_exp.experiment import Analyzer, CTX_PKT_IN_tmp, RuleSet
from rdfl_exp.utils.terminal import progress_bar


class FuzzMode(Enum):
    UNDEFINED   = 0,
    RANDOM      = 1,
    RULE        = 2,
    DELTA       = 3,
    BEADS       = 4
# End class FuzzMode


# noinspection PyUnresolvedReferences
class Experimenter:
    """
    The experimenter class is responsible for running any experience defined in a script under "scenarios"
    """

    # ===== ( Constructor ) ============================================================================================

    def __init__(self):

        self.__log = logging.getLogger(__name__)
        self.samples_per_iteration = 150

        self.__scenario         = None
        self.__scenario_name    = None
        self.__scenario_ctx = {
            'has_init'      : bool(),
            'has_before'    : bool(),
            'has_after'     : bool(),
            'has_term'      : bool()
        }
        self.__criterion = dict()
        self.__criterion_name = None

        self.__analyzer: Optional[Analyzer] = None

        # Fuzzing parameters
        self.fuzz_mode                      = FuzzMode.UNDEFINED
        self.ruleset: Optional[RuleSet]     = None
        self.enable_mutation                = True
        self.mutation_rate                  = 1.0
    # End def __init__

    # ===== ( Properties ) =============================================================================================

    @property
    def analyzer(self):
        return self.__analyzer
    # End def analyzer.getter

    @analyzer.setter
    def analyzer(self, obj):
        if isinstance(obj, Analyzer):
            self.__analyzer = obj
            if self.__scenario_name.startswith('onos') is True:
                self.__log.debug("Configuring Analyzer for ONOS controller")
                self.__analyzer.controller = 'onos'
            elif self.__scenario_name.startswith('ryu') is True:
                self.__analyzer.controller = 'ryu'
            elif self.__scenario_name is not None and self.__scenario_name != '':
                self.__log.warning("No known analyzer configuration for controller \"{}\"".format(self.__scenario_name.split("_")[0]))

        elif obj is None:
            self.__analyzer = None
        else:
            raise AttributeError("Expected object of type \'Analyzer\' or \'None\', not \'{}\'".format(type(obj)))
    # End def analyzer.setter

    @property
    def scenario(self):
        return self.__scenario_name

    @scenario.setter
    def scenario(self, name):
        """
        Set the scenario that should be used
        :param name: name of the scenario
        :return:
        """
        # Check if the scenario exists
        # TODO properly check the resources folder instead of assuming a set format
        scenario_pkg = "rdfl_exp.resources.scenarios.{0}.{0}".format(name)
        try:
            self.__scenario = importlib.import_module(scenario_pkg)
            # Register the scenario context
            self.__scenario_ctx['has_init']   = hasattr(self.__scenario, "initialize") and hasattr(self.__scenario.initialize, '__call__')
            self.__scenario_ctx['has_term']   = hasattr(self.__scenario, "terminate") and hasattr(self.__scenario.terminate, '__call__')
            self.__scenario_ctx['has_before'] = hasattr(self.__scenario, "before_each") and hasattr(self.__scenario.before_each, '__call__')
            self.__scenario_ctx['has_after']  = hasattr(self.__scenario, "after_each") and hasattr(self.__scenario.after_each, '__call__')

            # Check if the scenario as a test function
            if not hasattr(self.__scenario, "test") or not hasattr(self.__scenario.test, '__call__'):
                raise AttributeError("The function \"test\" is not defined in scenario \"{}\"".format(self.__scenario.__name__))

            if self.__analyzer is not None:
                if name.startswith('onos') is True:
                    self.__log.debug("Configuring Analyzer for ONOS controller")
                    self.__analyzer.controller = 'onos'
                elif name.startswith('ryu') is True:
                    self.__analyzer.controller = 'ryu'
                else:
                    self.__log.warning("No known analyzer configuration for controller \"{}\"".format(name.split("_")[0]))

        except ModuleNotFoundError as e:
            self.__log.error("Couldn't find scenario \"{}\".".format(name))
            raise e

        except AttributeError as e:
            self.__log.error(str(e))
            raise e

        except Exception as e:
            self.__log.exception("Uncaught exception while importing scenario \"{}\"".format(name))
            raise e

        else:
            self.__scenario_name = name
            self.__log.info("Loaded scenario {}".format(name))
    # End def set_scenario

    @property
    def criterion(self):
        return self.__criterion_name
    # End def criterion

    @criterion.setter
    def criterion(self, value: Union[str, Tuple[str, dict]]):
        """
        :param value:
        :return:
        """
        if isinstance(value, str):
            name = value
            kwargs = dict()
        else:
            name = value[0]
            kwargs = value[1]

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
                    # TODO: Maybe raise and error instead ?
                    self.__log.warning("No value defined to replace \"{}\" in criterion \"{}\"".format(_var, name))

            # Finally store the current criterion
            self.__log.info("Loaded criterion \"{}\"".format(name))
            self.__criterion = json.loads(criterion)

        except FileNotFoundError as e:
            self.__log.error("Couldn't find criterion \"{}\".".format(name))
            raise e
        else:
            self.__criterion_name = name
    # End def set_rule

    # ===== ( Run ) ====================================================================================================

    def run(self):
        """
        Main loop
        :return:
        """

        # ===== INITIALIZE =============================================================================================
        # Before running a test, run the "initialize" function of the scenario
        if self.__scenario_ctx['has_init'] is True:
            try:
                self.__log.debug("Running \"{}#initialize\"".format(self.__scenario.__name__))
                self.__scenario.initialize()

            except Exception as e:
                self.__log.exception("An exception occurred while running \"{}#initialize\"".format(self.__scenario.__name__))
                raise e

        # ===== MAIN TEST ==============================================================================================

        progress_bar(
            iteration=0,
            total=self.samples_per_iteration,
            prefix='Progress:',
            suffix='Complete ({}/{})'.format(0, self.samples_per_iteration),
            length=100
        )

        # Build the fuzzer instruction
        fuzz_instr = self.__build_fuzzer_instruction(count=self.samples_per_iteration)

        for i in range(self.samples_per_iteration):

            # Start a time
            start_time = timer()

            # ===== BEFORE EACH ========================================================================================
            # Try to run the 'before_each' function
            if self.__scenario_ctx['has_before'] is True:
                try:
                    self.__log.debug("Running \"{}#before_each\"".format(self.__scenario.__name__))
                    self.__scenario.before_each()
                except Exception as e:
                    self.__log.exception("An exception occurred while running \"{}#before_each\"".format(self.__scenario.__name__))
                    raise e

            # ===== TEST ===============================================================================================
            # Start the analysis before the core test
            if self.__analyzer is not None:
                self.__analyzer.start_analysis()

            # Try to run the 'test' function
            try:
                self.__log.debug("Running \"{}#test\"".format(self.__scenario.__name__))
                self.__scenario.test(instruction=fuzz_instr[i], retries=5)
            except Exception as e:
                self.__log.exception("An exception occurred while running \"{}#test\"".format(self.__scenario.__name__))
                raise e

            # Finish the analysis after the core test
            if self.__analyzer is not None:
                self.__analyzer.finish_analysis()

            # ===== AFTER EACH =========================================================================================
            # Try to run the 'after_each' function
            if self.__scenario_ctx['has_after'] is True:
                try:
                    self.__log.debug("Running \"{}#after_each\"".format(self.__scenario.__name__))
                    self.__scenario.after_each()
                except Exception as e:
                    self.__log.exception("An exception occurred while running \"{}#after_each\"".format(self.__scenario.__name__))
                    raise e

            # Stop the timer
            stop_time = timer()

            # Print log information
            self.__log.info("Test {} out of {} of scenario \"{}\" completed in {}s.".format(i + 1,
                                                                                            self.samples_per_iteration,
                                                                                            self.__scenario.__name__,
                                                                                            stop_time - start_time))

            # Increment the progress bar
            progress_bar(
                i + 1,
                self.samples_per_iteration,
                prefix='Progress:',
                suffix='Complete ({}/{})'.format(i + 1, self.samples_per_iteration),
                length=100
            )

        # ===== TERMINATE ==============================================================================================
        # If it's the last experiment, run the function on_last_instance
        if self.__scenario_ctx['has_term'] is True:
            try:
                self.__log.debug("Running \"{}#terminate\"".format(self.__scenario.__name__))
                self.__scenario.terminate()
            except Exception as e:
                self.__log.exception("An exception occurred while running \"{}#terminate\"".format(self.__scenario.__name__))
                raise e
    # End def run

    # ===== ( Private methods ) ========================================================================================

    def __build_fuzzer_instruction(self, count=1):
        """
        Build a fuzzer instruction depending on the fuzz mode
        :return: the fuzz action string
        """
        # Create an instruction list of "count" instructions
        instructions = list()

        # Perform a random mutation
        if self.fuzz_mode == FuzzMode.RANDOM:
            for i in range(count):
                # Create the dictionary
                json_dict = dict()
                json_dict.update(self.__criterion)
                json_dict['actions'] = [{
                    "intent": "mutate_packet",
                    "includeHeader": False
                }]
                instructions.append(json.dumps({"instructions": [json_dict]}))

        # Perform a byte mutation
        elif self.fuzz_mode == FuzzMode.DELTA:
            for i in range(count):
                # Create the dictionary
                json_dict = dict()
                json_dict.update(self.__criterion)
                json_dict['actions'] = [{
                    "intent": "mutate_bytes",
                    "includeHeader": False
                }]
                instructions.append(json.dumps({"instructions": [json_dict]}))

        elif self.fuzz_mode == FuzzMode.RULE:
            # Get the budget
            budget_list = self.__get_budget_for_rules(sample_size=count)

            for i in range(len(budget_list)):
                # Create the action for the rule i
                self.__log.trace("Budget for rule {}: {}".format(i, budget_list[i]))
                if budget_list[i] > 0:
                    actions = self.ruleset[i].convert_to_fuzzer_actions(
                        n=budget_list[i],
                        include_header=False,
                        enable_mutation=self.enable_mutation,
                        mutation_rate=self.mutation_rate if self.enable_mutation is True else 0.0,
                        ctx=CTX_PKT_IN_tmp
                    )
                    self.__log.trace("Number of actions generated for rule {}: {}".format(i, len(actions)))
                    for action in actions:
                        json_dict = dict()
                        json_dict.update(self.__criterion)  # add the criterion
                        json_dict['actions'] = [action]
                        instructions.append(json.dumps({"instructions": [json_dict]}))  # add it to the instruction
        else:
            raise RuntimeError("Cannot build instructions for {}".format(self.fuzz_mode))

        self.__log.trace("Number of instructions generated : {}".format(len(instructions)))
        return instructions
    # End def __build_fuzzer_action

    def __get_budget_for_rules(self, sample_size):
        budget_list = [self.ruleset[i].get_budget() * sample_size for i in range(len(self.ruleset))]
        rounded_budget = [int(x) for x in saferound(budget_list, places=0)]
        self.__log.trace("Calculated budget for {} rules: {}".format(len(self.ruleset), rounded_budget))
        return rounded_budget
    # End def __get_budget_for_rules

# End class Experimenter
