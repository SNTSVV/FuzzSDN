# -*- coding: utf-8 -*-
"""
Module used to parse the arguments of figsdn-report
"""

import argparse
import math
import sys
from typing import Iterable, Optional
from importlib import resources

from figsdn.common.utils import time_parse
from figsdn import __version__, __app_name__
from figsdn.common.utils import StrEnum
from figsdn.resources import scenarios, criteria


# ===== ( Enums ) ======================================================================================================

class Command(StrEnum):
    """Enum for the possible commands of figsdn."""

    # Values
    RUN         = 'run',

    @staticmethod
    def values():
        """Returns a list of all the possible commands"""
        return list(map(lambda c: c.value, Command))
# End class Command


class ErrorType(StrEnum):
    """Enum for the possible error type of figsdn."""
    # Positional argument to choose the target
    UNKNOWN_REASON      = 'unknown_reason',
    KNOWN_REASON        = 'known_reason',
    PARSING_ERROR       = 'parsing_error',
    NON_PARSING_ERROR   = 'non_parsing_error',
    OFP_BAD_OUT_PORT    = 'ofp_bad_out_port'

    @staticmethod
    def values():
        """Returns a list of all the possible commands"""
        return list(map(lambda c: c.value, ErrorType))
# End class ErrorType


class Method(StrEnum):
    """Enum for the possible fuzzing methods of figsdn."""
    DEFAULT = 'default',
    DELTA   = 'DELTA',
    BEADS   = 'BEADS',

    @staticmethod
    def values():
        """Returns a list of all the possible mode"""
        return list(map(lambda c: c.value, Method))
# End class Mode


class Budget(StrEnum):
    """Enum for the methods of budget calculation"""

    CONFIDENCE              = 'confidence',
    CONFIDENCE_AND_RANK     = 'rank-confidence',

    @staticmethod
    def values():
        """Returns a list of all the possible mode"""
        return list(map(lambda c: c.value, Budget))
# End class Mode


class Limit(StrEnum):
    """Enum for the possible limits to a run of figsdn."""

    TIME        = 'time',
    ITERATION   = 'iteration',
    BALANCE     = 'balance'
# End class Mode


# ===== ( Arg Range for floats ) =======================================================================================

class ArgRange(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __eq__(self, other):
        return self.start <= other <= self.end

    def __contains__(self, item):
        return self.__eq__(item)

    def __iter__(self):
        yield self

    def __repr__(self):
        return '[{0},{1}]'.format(self.start, self.end)
# End def ArgRAnge


# ===== ( Scenario ans Criteria list ) ================================================================================

SCENARIOS = list(sorted(
    s for s in resources.contents(scenarios) if s not in ['__pycache__', '__init__.py'])
)

CRITERIA  = list(sorted(
    c.replace('.json', '') for c in resources.contents(criteria) if c not in ['__pycache__', '__init__.py'])
)


# ===== ( Argument Parse Function ) ====================================================================================

def parse(args: Optional[Iterable] = None):

    """
    Parse the arguments passed to the program.
    """
    parser = argparse.ArgumentParser(
        description="A Failure-Inducing Model generation scheme for SDN based systems using Fuzzing and Machine "
                    "Learning Techniques",
    )

    # ==== ( Global Optional arguments ) ===============================================================================

    parser.add_argument(
        '--version',
        action='version',
        version="{} {}".format(__app_name__, __version__)
    )

    parser.add_argument(
        '--no-clean',
        action='store_false',
        help="Do not perform cleaning actions on exit"
    )

    # ==== ( command argument ) ========================================================================================

    command_parser = parser.add_subparsers(
        title='command',
        dest='command',
        required=True,
        metavar='COMMAND',
        help="Command to be executed."
    )

    # ==== ( Run Command arguments ) ===================================================================================

    run_cmd = command_parser.add_parser(
        name=Command.RUN,
        help='Run an experiment.'
    )

    run_cmd.add_argument(
        'error_type',
        metavar='ERROR_TYPE',
        type=str,
        choices=ErrorType.values(),
        help="Choose the error type to detect. "
             "Allowed values are: {}".format(', '.join("\'{}\'".format(e) for e in ErrorType.values()))
    )

    # Positional argument to choose the machine learning algorithm
    run_cmd.add_argument(
        'scenario',
        metavar='SCENARIO',
        type=str,
        choices=SCENARIOS,
        help="Name of the scenario to be run. "
             "Allowed values are: {}".format(', '.join("\'{}\'".format(scn) for scn in SCENARIOS))
    )

    # Positional argument to choose the criterion
    # Break criterion positional argument in two names to circumvent a bug where a positional argument can't have
    # several kwargs defined (python issue 14074: https://bugs.python.org/issue14074)
    run_cmd.add_argument(
        'criterion_name',
        metavar='CRITERION',
        type=str,
        choices=CRITERIA,
        help="Name of the criterion to be run. "
             "Allowed values are: {}".format(', '.join("\'{}\'".format(crit) for crit in CRITERIA))
    )

    run_cmd.add_argument(
        'criterion_kwargs',
        metavar='kwargs',
        nargs='*',
        type=str,
        help="kwargs for the criterion (optional)"
    )

    # ==== ( Run Command Optionals ) ===================================================================================

    # Argument to choose the machine learning algorithm
    run_cmd.add_argument(
        '-A,',
        '--algorithm',
        metavar='',
        type=str,
        default='RIPPER',
        dest='algorithm',
        help="Select which Machine Learning algorithm to use. (default: \"%(default)s\")"
    )

    # Argument to choose the machine learning algorithm
    run_cmd.add_argument(
        '-b,',
        '--budget',
        metavar='',
        type=str,
        default=Budget.CONFIDENCE_AND_RANK.value,
        choices=Budget.values(),
        dest='budget',
        help="Select which Machine Learning algorithm to use. (default: \"%(default)s\"). "
             "Allowed values are: {}".format(', '.join("\'{}\'".format(bgt) for bgt in Budget.values()))
    )

    # Argument to choose the number of cross validation folds
    run_cmd.add_argument(
        '--cv-folds',
        metavar='',
        type=int,
        default=10,
        choices=ArgRange(2, math.inf),
        dest='cv_folds',
        help="Define the number of folds to use during cross-validation. (default: %(default)s)"
    )

    # Argument to limit the number of iterations
    run_cmd.add_argument(
        '-l',
        '--limit',
        metavar='',
        type=str,
        default=None,
        nargs=2,
        dest='limit',
        help="Stops the {} after a given number of iterations. The current iteration will be finished however."
    )

    # Argument to choose the preprocessing strategy
    run_cmd.add_argument(
        '-F',
        '--filter',
        metavar='',
        type=str,
        default=None,
        dest='filter',
        help="Select which preprocessing strategy to use. (default: \"%(default)s\")"
    )

    # Argument to choose the experiment mode
    run_cmd.add_argument(
        '--method',
        metavar='',
        type=str,
        choices=Method.values(),
        default=Method.DEFAULT.value,
        dest='method',
        help="Select the method of fuzzing. "
             "Allowed modes are: {}".format(', '.join("\'{}\'".format(m) for m in Method.values()))
    )

    # Argument to choose the mutation rate of additional fields
    run_cmd.add_argument(
        '--mutation-rate',
        metavar='',
        type=float,
        default=1.0,
        choices=ArgRange(0.0, math.inf),
        dest='mutation_rate',
        help="Sets the mutation rate of additional fields upon rule application. (default: %(default)s)"
    )

    # Argument to choose the reference name of the experiment
    run_cmd.add_argument(
        '-R',
        '--reference',
        metavar='',
        type=str,
        default=None,
        dest='reference',
        help="Reference to be used for the experiment"
    )

    # Argument to choose the number of sample to generate
    run_cmd.add_argument(
        '-s',
        '--samples',
        metavar='',
        type=int,
        default=200,
        dest='samples',
        help="Override the number of samples. (default: %(default)s)"
    )

    args = parser.parse_args(sys.argv[1:] if args is None else args)
    return _format_args(parser, args)
# End def parse


# ===== ( Module Private Functions ) ===================================================================================

def _format_args(parser : argparse.ArgumentParser, args : argparse.Namespace):
    """ Perform some operations on the arguments."""

    # TODO: All this sections should be removed and integrated within the experimenter
    setattr(args, 'target_class', args.error_type)
    delattr(args, 'error_type')
    setattr(args, 'other_class', None)

    if args.target_class == ErrorType.KNOWN_REASON:
        args.other_class = ErrorType.UNKNOWN_REASON.value

    elif args.target_class == ErrorType.UNKNOWN_REASON:
        args.other_class = ErrorType.KNOWN_REASON.value

    elif args.target_class == ErrorType.PARSING_ERROR:
        args.other_class = ErrorType.NON_PARSING_ERROR.value

    elif args.target_class == ErrorType.NON_PARSING_ERROR:
        args.other_class = ErrorType.PARSING_ERROR.value

    elif args.target_class == ErrorType.OFP_BAD_OUT_PORT:
        args.other_class = "OTHER_REASON"

    # Format the criterion
    if args.criterion_kwargs:
        kwargs = dict()
        for kwarg in args.criterion_kwargs:
            name, value = kwarg.split("=")
            kwargs[name] = value
        args.criterion_kwargs = kwargs
    else:
        args.criterion_kwargs = dict()

    # Format the date of time_limit
    if args.limit:
        if args.limit[0] == Limit.TIME:
            tmp = time_parse(args.limit[1])
            if tmp is None:
                parser.error("Invalid time format. (got : \'{}\')".format(args.limit[1]))
            else:
                args.limit[1] = tmp

    return args
# End def _format_args
