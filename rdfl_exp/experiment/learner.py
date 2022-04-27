#!/usr/bin/env python3
# coding: utf-8
import logging
import os
import re
from copy import copy
from typing import Dict, NamedTuple, Optional, Tuple

from weka.classifiers import Classifier, Evaluation, FilteredClassifier
from weka.core import jvm
from weka.core.classes import Random
from weka.core.converters import Loader
from weka.core.dataset import Instances
from weka.filters import Filter, MultiFilter

from rdfl_exp.experiment import Rule, RuleSet
from rdfl_exp.utils import str_to_typed_value
from rdfl_exp.utils.log import add_logging_level


class ModelInfo(NamedTuple):
    """
    The metadata of a model.
    """
    # The classes used by the model
    classes : Tuple[str, str]

    # Evaluation method
    evaluation_method : Optional[str]
    instances         : int

    # Accuracy, number of TP, FP, TN, FN
    accuracy: float
    num_tp  : Dict[str, int]
    num_fp  : Dict[str, int]
    num_tn  : Dict[str, int]
    num_fn  : Dict[str, int]

    # The Precision and Recall and F-Measure for each class
    precision   : Dict[str, float]
    recall      : Dict[str, float]
    f_measure   : Dict[str, float]

    # The mcc, auroc and auprc values
    mcc     : Dict[str, float]
    auroc   : Dict[str, float]
    auprc   : Dict[str, float]
# End class ModelInfo


class Model:
    """
    Utility class that stores the results from a Learner
    """

    def __init__(
            self,
            classifier      : Classifier,
            evaluator       : Evaluation,
            class_label     : Optional[Dict[int, str]] = None
    ):
        self._classifier    = classifier
        self._ruleset       : RuleSet
        self._info          : ModelInfo

        # 0. If no dictionary of class labels has been given, just craft one with basic names
        if class_label is None:
            class_label = {0: '0', 1: '1'}

        # 1. Extract the rules from the classifier
        self._ruleset = RuleSet()
        lines = self._classifier.__str__().split("\n")
        for line in lines:
            # Check if the line match the structure of a rule
            if re.match(r'(.*)=>(.*=.*\(.*/.*\))', line):
                rule = Rule.from_string(line)
                if rule is not None:
                    self._ruleset.add_rule(rule)
        self._ruleset.canonicalize()

        # 3. Create the model info
        self._info = ModelInfo(
            classes=(class_label[0], class_label[1]),
            evaluation_method="cross_validation",  # TODO: Determine the eval_method depending on the evaluator java class
            instances=int(evaluator.num_instances),
            accuracy=evaluator.percent_correct,
            num_tp={
                class_label[0]: int(evaluator.num_true_positives(0)),
                class_label[1]: int(evaluator.num_true_positives(1))
            },
            num_fp={
                class_label[0]: int(evaluator.num_false_positives(0)),
                class_label[1]: int(evaluator.num_false_positives(1))
            },
            num_tn={
                class_label[0]: int(evaluator.num_true_negatives(0)),
                class_label[1]: int(evaluator.num_true_negatives(1))
            },
            num_fn={
                class_label[0]: int(evaluator.num_false_negatives(0)),
                class_label[1]: int(evaluator.num_false_negatives(1))
            },
            precision={
                class_label[0]: evaluator.precision(0),
                class_label[1]: evaluator.precision(1)
            },
            recall={
                class_label[0]: evaluator.recall(0),
                class_label[1]: evaluator.recall(1)
            },
            f_measure={
                class_label[0]: evaluator.f_measure(0),
                class_label[1]: evaluator.f_measure(1)
            },
            mcc={
                class_label[0]: evaluator.matthews_correlation_coefficient(0),
                class_label[1]: evaluator.matthews_correlation_coefficient(1)
            },
            auroc={
                class_label[0]: evaluator.area_under_roc(0),
                class_label[1]: evaluator.area_under_roc(1)
            },
            auprc={
                class_label[0]: evaluator.area_under_prc(0),
                class_label[1]: evaluator.area_under_prc(1)
            }
        )
    # End def __init__

    # ===== ( Getters ) ================================================================================================

    @property
    def classifier(self):
        return self._classifier
    # End def classifier

    @property
    def info(self):
        return self._info
    # End def info

    @property
    def ruleset(self):
        return self._ruleset
    # End def ruleset

    @property
    def has_rules(self):
        """
        Returns True if there are rules in the ruleset else False
        :return: bool
        """
        if self.ruleset is not None:
            return self.ruleset.has_rules()
        else:
            return False
    # End def has_rules

    # ===== ( Methods ) ================================================================================================

    def save(self, file_path):
        """
        Serialize the classifier and save it under 'file_path' to be reused later.
        :param file_path: the file to save the model to
        :type: str
        """
        self._classifier.serialize(file_path, header=self._classifier.header)
    # End def save

    def reevaluate(self, data_path: str):
        """

        :param data_path:
        :return:
        """

        loader = Loader("weka.core.converters.ArffLoader")
        dataset = loader.load_file(data_path)
        dataset.class_is_last()

        class_label = {
                0: dataset.attribute(dataset.class_index).value(0),
                1: dataset.attribute(dataset.class_index).value(1)
            }

        evaluator = Evaluation(dataset)
        evaluator.test_model(self.classifier, dataset)

        return ModelInfo(
            classes=(class_label[0], class_label[1]),
            evaluation_method="test_data: {}".format(data_path),
            instances=int(evaluator.num_instances),
            accuracy=evaluator.percent_correct,
            num_tp={
                class_label[0]: int(evaluator.num_true_positives(0)),
                class_label[1]: int(evaluator.num_true_positives(1))
            },
            num_fp={
                class_label[0]: int(evaluator.num_false_positives(0)),
                class_label[1]: int(evaluator.num_false_positives(1))
            },
            num_tn={
                class_label[0]: int(evaluator.num_true_negatives(0)),
                class_label[1]: int(evaluator.num_true_negatives(1))
            },
            num_fn={
                class_label[0]: int(evaluator.num_false_negatives(0)),
                class_label[1]: int(evaluator.num_false_negatives(1))
            },
            precision={
                class_label[0]: evaluator.precision(0),
                class_label[1]: evaluator.precision(1)
            },
            recall={
                class_label[0]: evaluator.recall(0),
                class_label[1]: evaluator.recall(1)
            },
            f_measure={
                class_label[0]: evaluator.f_measure(0),
                class_label[1]: evaluator.f_measure(1)
            },
            mcc={
                class_label[0]: evaluator.matthews_correlation_coefficient(0),
                class_label[1]: evaluator.matthews_correlation_coefficient(1)
            },
            auroc={
                class_label[0]: evaluator.area_under_roc(0),
                class_label[1]: evaluator.area_under_roc(1)
            },
            auprc={
                class_label[0]: evaluator.area_under_prc(0),
                class_label[1]: evaluator.area_under_prc(1)
            }
        )

    # End def reevaluate
# End class Model


class Learner:
    """
    The learner class is responsible for acquiring the results from an Experimenter, and learn and create a model.
    """

    def __init__(self):

        # Sets the logger
        self.log = logging.getLogger(__name__)

        # Classification
        self.target_class   : str = "0"
        self.other_class    : str = "1"

        # ML Algorithms
        self._ml_alg_full   : Optional[str] = None
        self._ml_alg        : Optional[str] = None
        self._ml_hp         : Optional[dict] = None

        # pp_strat
        self._filter_full   : Optional[str] = None
        self._filter        : Optional[str] = None
        self._filter_hp     : Optional[dict] = None

        # Learning Parameters
        self._seed          : Optional[int] = None
        self._cv_folds      : int = 10

        # Dataset
        self.dataset        : Optional[Instances] = None

    # ===== ( Setters ) ================================================================================================

    @property
    def seed(self):
        return self._seed
    # End def seed

    @property
    def cv_folds(self):
        return self._cv_folds
    # End def cv_folds

    @property
    def algorithm(self):
        return self._ml_alg_full
    # End def machine_learning_algorithm

    @property
    def filter(self):
        return self._filter
    # End def machine_learning_algorithm

    # ===== ( Setters ) ================================================================================================

    @seed.setter
    def seed(self, value):
        if value is None:
            self._seed = None
            self.log.debug("seed set to clock time")
        elif isinstance(value, int) or isinstance(value, float):
            self._seed = value
            self.log.debug("seed set to {}".format(int(value)))
        else:
            raise AttributeError("Attribute \"seed\" must be either None, int or float (not: {})".format(type(value)))
    # End def seed

    @cv_folds.setter
    def cv_folds(self, value):
        # If cv_folds > 0, perform cross validation
        if isinstance(value, (int, float)) and value > 1:
            self._cv_folds = int(value)
            self.log.debug("cross-validation folds number set to \"{}\"".format(self._cv_folds))
        else:
            ValueError("cv_folds folds must be an int >= 1 (got: \"{}\")".format(value))
    # End def cv_folds.setter

    @algorithm.setter
    def algorithm(self, alg: str):
        self._ml_alg_full = copy(alg)
        alg_split = alg.split(',')

        self._ml_alg = alg_split[0].upper()
        self._ml_hp = None
        self.log.debug("machine learning algorithm set to \"{}\"".format(alg))

        # parse the hyper-parameters
        if len(alg_split) > 1:
            self._ml_hp = dict()
            for param in alg_split[1:]:
                key, value = param.split('=')
                self._ml_hp[key.strip()] = str_to_typed_value(value.strip())
    # End def algorithm.setter

    @filter.setter
    def filter(self, filter_):
        self._filter_full = copy(filter_)
        pp_split = filter_.split(',')
        self._filter_hp = None
        self._filter = pp_split[0].upper()
        self.log.debug("preprocess_strategy set to \"{}\"".format(filter_))

        # parse the hyper-parameters
        if len(pp_split) > 1:
            self._filter_hp = dict()
            for param in pp_split[1:]:
                key, value = param.split('=')
                self._filter_hp[key.strip()] = str_to_typed_value(value.strip())
    # End def filter.setter

    # ===== ( Getters ) ================================================================================================

    def get_instances_count(self) -> Dict[str, int]:
        if self.dataset is None:
            self.log.error("Requesting dataset size, while no dataset was loaded")
            raise RuntimeError("No dataset loaded.")

        target_cnt = other_cnt = 0
        for data in self.dataset:
            if data.get_string_value(self.dataset.class_index) == self.target_class:
                target_cnt += 1
            else:
                other_cnt += 1

        return {
                   'all': len(self.dataset),
                   self.target_class: target_cnt,
                   self.other_class: other_cnt
        }
    # End def get_instances_count

    # ===== ( Public function ) ========================================================================================

    def load_data(self, data_path):
        # load data from arff file
        self.log.info("Loading data from \"{}\"".format(data_path))
        loader = Loader("weka.core.converters.ArffLoader")

        self.dataset = loader.load_file(data_path)
        self.dataset.class_is_last()

    # End def load_data

    def learn(self):
        """
        """
        # Build the classifier
        self.log.info("Learning from \"{}\" using \"{}\"".format(self.dataset.relationname, self._ml_alg))

        # Reset the results, context, classifier, evaluator, ...
        classifier      : Classifier
        evaluator       : Evaluation

        # Create the filter to balance the data
        filter_ = None
        if self._filter is not None and self._filter != '':
            self.log.debug("Building the filter for the preprocessing strategy \"{}\"...".format(self._filter))
            try:
                pp_fltr = self.__build_pp_filters()
                if len(pp_fltr) > 1:  # Multiple filters
                    filter_ = MultiFilter()
                    for f in pp_fltr:
                        filter_.append(f)
                elif len(pp_fltr) == 1:  # One filter
                    filter_ = pp_fltr[0]
                else:
                    # If the implementation for __build_pp_filter is correct, we should never reach this point.
                    # If an empty filter is returned and it is not normal or it requires a warning, this should be done
                    # in the __build_pp_filter function directly.
                    pass
            except ValueError as e:
                # A value error is risen only when the preprocess strategy is not known
                self.log.error("Couldn't apply strategy {} with error \"{}\"".format(self._filter, str(e)))
                self.log.warning("Machine learning will be performed without any data preprocessing.")

        # Create the classifier
        self.log.debug("Creating the classifier...")
        clf_ = None
        if self._ml_alg == 'RIPPER':
            # NOTE: This is a simple solution for handling the hyper-parameters. a more complex solution might be needed
            #       in the future.
            options = None
            if self._ml_hp:
                options = list()
                for key in self._ml_hp.keys():
                    # Number of folds
                    if key == 'nof':
                        options.extend(('-F', str(self._ml_hp[key])))
                    # Minimum total weight
                    if key == 'mtw':
                        options.extend(('-N', str(self._ml_hp[key])))
                    # Number of optimization runs
                    if key == 'o':
                        options.extend(('-O', str(self._ml_hp[key])))
                    # Check error rate
                    if key == 'cer' and self._ml_hp[key] is False:
                        options.append('-E')
                    # Use Pruning
                    if key == 'up' and self._ml_hp[key] is False:
                        options.append('-P')

            clf_ = Classifier(classname="weka.classifiers.rules.JRip", options=options)
        else:
            raise ValueError("Classifying algorithm \"{}\" is not supported.".format(self._ml_alg))

        # Create the final classifier
        if filter_ is None:
            classifier = clf_
        else:
            classifier              = FilteredClassifier()
            classifier.filter       = filter_
            classifier.classifier   = clf_

        # Perform cross validation on the dataset
        self.log.debug("Performing classifier evaluation...")
        evaluator = Evaluation(self.dataset)

        # Sets the seed for this learning iteration
        self.log.debug("Building the classifier...")
        seed = self._seed if self._seed is not None else int.from_bytes(os.urandom(7), 'big')
        evaluator.crossvalidate_model(classifier, self.dataset, self._cv_folds, Random(seed))
        self.log.trace("Done. Evaluator:\n{}\n{}".format(evaluator.summary(), evaluator.class_details("Statistics:")))

        # Build the classifier
        self.log.debug("Building the classifier...")
        classifier.build_classifier(self.dataset)
        self.log.trace("Done. Classifier:\n{}".format(classifier))

        # Create the model
        return Model(
            classifier=classifier,
            evaluator=evaluator,
            class_label={
                0: self.dataset.attribute(self.dataset.class_index).value(0),
                1: self.dataset.attribute(self.dataset.class_index).value(1)
            }
        )
    # End def learn

    # ===== ( Private Functions ) ======================================================================================

    def __build_pp_filters(self):
        """
        Perform some preprocessing on the data depending on the strategy defined.
        If a strategy is not implemented, an error will be risen.

        :param strategy (str): the strategy to be used to preprocess the data
        :return:
        """

        # Exit the function if there is no preprocessing strategy defined
        if self._filter is None:
            self.log.warning("function \"__build_pp_filters\" was called while there is no pp_strategy defined")
            return

        filters = []
        # Balancing the dataset using under sampling method
        if self._filter == 'UNDERSAMPLING':
            self.log.info("Creating filter for \"{}\" strategy".format(self._filter))
            filters.append(
                Filter(classname="weka.filters.supervised.instance.SpreadSubsample", options=["-M", "1.0"])
            )

        # Balancing the dataset using w
        elif self._filter == 'WEIGHT_BALANCING':
            self.log.info("Using \"{}\" data preprocessing strategy".format(self._filter))
            filters.append(
                Filter(classname="weka.filters.supervised.instance.ClassBalancer", options=["-num-intervals", "10"])
            )

        elif self._filter.startswith("SMOTE"):

            nn = 5
            if self._filter_hp:
                for key in self._filter_hp.keys():
                    # Nearest neighbors
                    if key == 'nn':
                        nn = int(self._filter_hp[key])

            # get the number of neighbours to consider
            self.log.info("Using \"SMOTE-{}\" data preprocessing strategy".format(nn))

            # compute the number of instances for each class and compute the smote factor
            index_list = (str(i + 1) for i in range(self.dataset.class_index))
            class1_cnt, class2_cnt = 0, 0
            for data in self.dataset:
                if int(data.get_value(data.class_index)) == 0:
                    class1_cnt += 1
                else:
                    class2_cnt += 1
            min_cls_cnt = min(class1_cnt, class2_cnt)
            max_cls_cnt = max(class1_cnt, class2_cnt)
            percentage = 100 * (max_cls_cnt - min_cls_cnt) / min_cls_cnt  # Default percentage
            if self._ml_hp:
                # Sets a target ratio below 0.5
                if 'target-ratio' in self._ml_hp:
                    target_ratio = max(0.0, min(0.5, float(self._ml_hp['target-ratio'])))
                    if min_cls_cnt / (min_cls_cnt + max_cls_cnt) < target_ratio:
                        percentage *= (target_ratio / 0.5)  # Make the percentage to be close to the target ratio
                    else:
                        percentage = 0.0  # If within the target ratio range then nothing should be done

                if 'threshold' in self._ml_hp:
                    if min(class1_cnt, class2_cnt) / (class1_cnt + class2_cnt) > max(0.0,
                                                                                     float(self._ml_hp['threshold'])):
                        percentage = 0.0

                if 'multiplier' in self._ml_hp:
                    percentage *= max(0.0, float(self._ml_hp['multiplier']))

            # Create the filters
            filters.append(
                Filter(
                    classname="weka.filters.supervised.instance.SMOTE",
                    options=[
                        '-K', str(nn),
                        '-P', str(percentage)
                    ]
                )
            )
            filters.append(
                Filter(
                    classname="weka.filters.unsupervised.attribute.NumericTransform",
                    options=[
                        '-C', "java.lang.Math",
                        '-M', "ceil",
                        '-R', ','.join(index_list)
                    ]
                )
            )

        else:
            raise ValueError("Unknown strategy: {}".format(self._filter))

        return filters
    # End def _build_pp_filters
# End class Learner

if __name__ == '__main__':

    jvm.start(packages=True)
    add_logging_level('TRACE', logging.DEBUG - 5)
    try:
        learner = Learner()
        learner.target_class = 'unknown_reason'
        learner.other_class = 'known_reason'
        learner.algorithm = 'RIPPER'
        learner.load_data('/Users/raphael.ollando/it_20_copy.arff')

        model = learner.learn()
        print(model.info)
        model.save('/Users/raphael.ollando/serialized_model.model')


    finally:
        jvm.stop()