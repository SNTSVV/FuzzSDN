#!/usr/bin/env python3
# coding: utf-8
import logging
import os
import re
from copy import copy

from weka.classifiers import Classifier, Evaluation, FilteredClassifier
from weka.core.classes import Random
from weka.core.converters import Loader
from weka.filters import Filter, MultiFilter

from rdfl_exp.experiment import Rule, RuleSet


class Learner:
    """
    The learner class is responsible for acquiring the results from an Experimenter, and learn and create a model.
    """

    def __init__(self):

        # Sets the logger
        self.log = logging.getLogger(__name__)

        # Sets variables
        self.target_class   = "1"
        self.other_class    = "2"
        self.seed           = None
        self.ml_alg         = None
        self.pp_strat       = None
        self.cv_folds       = 10

        # Dataset
        self.dataset        = None

        # result variables
        self.context        = dict()
        self.result         = dict()
        self.ruleset        = None
        self.classifier     = None
        self.evl_cv         = None
        self.evl_bld        = None

    # ===== ( Setters ) ================================================================================================

    def set_classes(self, target_class : str, other_class : str):
        self.target_class = target_class
        self.other_class = other_class
        self.log.debug("Target class set to \"{}\". Other class set to \"{}\".".format(target_class, other_class))
    # End def set_cross_validation_folds

    def set_seed(self, seed):
        if seed is None:
            self.seed = None
            self.log.debug("seed set to clock time")
        elif isinstance(seed, int):
            self.seed = seed
            self.log.debug("seed set to {}".format(seed))
        else:
            raise AttributeError("Attribute \"seed\" must be either None or an int (not: {})".format(type(seed)))
    # End def set_seed

    def set_learning_algorithm(self, alg : str):
        self.ml_alg = alg.upper()
        self.log.debug("machine learning algorithm set to \"{}\"".format(alg))
    # End def set_learning_algorithm

    def set_preprocessing_strategy(self, pp_strat):
        self.pp_strat = pp_strat
        self.log.debug("preprocess_strategy set to \"{}\"".format(pp_strat))
    # End def set_preprocess_strategy

    def set_cross_validation_folds(self, cv_folds : int):
        self.cv_folds = cv_folds
        self.log.debug("cross-validation folds number set to \"{}\"".format(cv_folds))
    # End def set_cross_validation_folds

    # ===== ( Getters ) ================================================================================================

    def get_rules(self) -> RuleSet:
        return self.ruleset
    # End def get_ruleset

    def get_evaluators(self):
        return self.evl_cv, self.evl_bld
    # End def get_evaluators

    def get_context(self) -> dict:
        return self.context
    # End def get_context

    def get_results(self) -> dict:
        return self.result
    # End def get_results

    def get_dataset_size(self) -> int:
        if self.dataset is None:
            self.log.error("Requesting dataset size, while no dataset was loaded")
            raise RuntimeError("No dataset loaded.")

        return len(self.dataset)
    # End def dataset_size

    def get_size_of_classes(self):
        if self.dataset is None:
            self.log.error("Requesting dataset size, while no dataset was loaded")
            raise RuntimeError("No dataset loaded.")

        target_cnt = other_cnt = 0
        for data in self.dataset:
            if data.get_string_value(self.dataset.class_index) == self.target_class:
                target_cnt += 1
            else:
                other_cnt += 1

        return target_cnt, other_cnt
    # End def get_number_of_instances

    def has_rules(self):
        if self.ruleset is not None:
            return self.ruleset.has_rules()
        else:
            return False
    # End def has_rules

    # ===== ( Learning function ) ======================================================================================

    def load_data(self, data_path):
        # load data from arff file
        self.log.info("Loading data from \"{}\"".format(data_path))
        loader = Loader("weka.core.converters.ArffLoader")

        self.dataset = loader.load_file(data_path)
        self.dataset .class_is_last()
    # End def load_data

    def learn(self):
        """
        """

        # Build the classifier
        self.log.info("Building classifier using \"{}\" algorithm".format(self.ml_alg))

        # Reset the results, context, classifier, evaluator, ...
        self.context    = dict()
        self.result     = dict()
        self.ruleset    = None
        self.classifier = None
        self.evl_cv     = None
        self.evl_bld    = None

        # Create the filter to balance the data
        _fltr = None
        if self.pp_strat is not None and self.pp_strat != '':
            self.log.debug("Building the filter for the preprocessing strategy \"{}\"...".format(self.pp_strat))
            try:
                pp_fltr = self.__build_pp_filters()
                if len(pp_fltr) > 1:  # Multiple filters
                    _fltr = MultiFilter()
                    for f in pp_fltr:
                        _fltr.append(f)
                elif len(pp_fltr) == 1:  # One filter
                    _fltr = pp_fltr[0]
                else:
                    # If the implementation for __build_pp_filter is correct, we should never reach this point.
                    # If an empty filter is returned and it is not normal or it requires a warning, this should be done
                    # in the __build_pp_filter function directly.
                    pass
            except ValueError as e:
                # A value error is risen only when the preprocess strategy is not known
                self.log.error("Couldn't apply strategy {} with error \"{}\"".format(self.pp_strat, str(e)))
                self.log.warning("Machine learning will be performed without any data preprocessing.")

        # Create the classifier
        self.log.debug("Creating the classifier...")
        _clf = None
        if self.ml_alg == 'RIPPER':
            _clf = Classifier(classname="weka.classifiers.rules.JRip")
            self.context['algorithm'] = "RIPPER"
        else:
            raise ValueError("Classifying algorithm \"{}\" is not supported.".format(self.ml_alg))

        # Create the final classifier
        if _fltr is None:
            self.classifier = _clf
        else:
            self.classifier             = FilteredClassifier()
            self.classifier.filter      = _fltr
            self.classifier.classifier  = _clf

        # Perform cross validation on the dataset
        self.log.debug("Performing classifier evaluation...")
        self.evl_cv = Evaluation(self.dataset)
        # If cv_folds > 0, perform cross validation
        if not isinstance(self.cv_folds, int) or self.cv_folds < 1:
            ValueError("The number of cross-validation folds must be an integer >= 1 (got: \"{}\")".format(self.cv_folds))

        # Sets the seed for this learning iteration
        seed = copy(self.seed) if self.seed is not None else int.from_bytes(os.urandom(7), 'big')
        self.evl_cv.crossvalidate_model(self.classifier, self.dataset, self.cv_folds, Random(seed))
        self.log.debug("Evaluator:\n{}\n{}".format(self.evl_cv.summary(),
                                                   self.evl_cv.class_details("Statistics:")))

        # Fill the context
        self.context['cv_folds'] = self.cv_folds
        self.context['seed'] = seed

        # Build the classifier
        self.log.debug("Building the classifier...")
        self.classifier.build_classifier(self.dataset)
        self.evl_bld = Evaluation(self.dataset)
        self.evl_bld.test_model(self.classifier, self.dataset)
        self.log.debug("Classifier:\n{}".format(self.classifier))

        # Extract the  rules from the classifier
        self.log.debug("Extracting the rules...")
        self.ruleset = RuleSet()
        lines = self.classifier.__str__().split("\n")
        for line in lines:
            # Check if the line match the structure of a rule
            if re.match(r'(.*)=>(.*=.*\(.*/.*\))', line):
                rule = Rule.from_string(line)
                if rule is not None:
                    self.ruleset.add_rule(rule)
        # Canonicalize the ruleset
        self.ruleset.canonicalize()

        self.log.debug("Extracting the results from the generated rules...")
        self.result['cross-validation'] = _get_stats_from_evaluator(self.evl_cv,  (self.target_class, self.other_class))
        self.result['evaluation']       = _get_stats_from_evaluator(self.evl_bld, (self.target_class, self.other_class))
    # End def learn

    # ===== ( Helper Functions ) =======================================================================================

    # def _preprocess_data(strategy: str, dataset: Union[Instances, list[Instances]]) -> Union[Instances, list[Instances]]:
    def __build_pp_filters(self):
        """
        Perform some preprocessing on the data depending on the strategy defined.
        If a strategy is not implemented, an error will be risen.

        :param strategy (str): the strategy to be used to preprocess the data
        :return:
        """

        # Exit the function if there is no preprocessing strategy defined
        if self.pp_strat is None:
            self.log.warning("function \"__build_pp_filters\" was called while there is no pp_strategy defined")
            return

        filters = []
        self.context["pp_filter"] = dict()
        # Balancing the dataset using under sampling method
        if self.pp_strat == 'UNDERSAMPLING':
            self.log.info("Creating filter for \"{}\" strategy".format(self.pp_strat))
            filters.append(
                Filter(classname="weka.filters.supervised.instance.SpreadSubsample", options=["-M", "1.0"])
            )

            # Fill the last results info
            self.context["pp_filter"]["strategy"] = "undersampling"
            self.context["pp_filter"]["target_ratio"] = 0.5

        # Balancing the dataset using w
        elif self.pp_strat == 'WEIGHT_BALANCING':
            self.log.info("Using \"{}\" data preprocessing strategy".format(self.pp_strat))
            filters.append(
                Filter(classname="weka.filters.supervised.instance.ClassBalancer", options=["-num-intervals", "10"])
            )

            # Fill the context if there is one
            self.context["pp_filter"]["strategy"] = "weight_balancing"
            self.context["pp_filter"]["num-intervals"] = 10

        elif self.pp_strat.startswith("SMOTE"):
            match = re.match(r'SMOTE-?(?P<n>\d*)?', self.pp_strat)

            # get the number of neighbours to consider
            n = int(match.group("n")) if match.group("n") != '' else 5
            self.log.info("Using \"SMOTE-{}\" data preprocessing strategy".format(n))

            # compute the number of instances for each class and compute the smote factor
            index_list = (str(i + 1) for i in range(self.dataset.class_index))
            class1_cnt, class2_cnt = 0, 0
            for data in self.dataset:
                if int(data.get_value(data.class_index)) == 0:
                    class1_cnt += 1
                else:
                    class2_cnt += 1
            smote_factor = 100 * (max(class1_cnt, class2_cnt) - min(class1_cnt, class2_cnt)) / min(class1_cnt,
                                                                                                   class2_cnt)

            # Create the filters
            filters.append(
                Filter(
                    classname="weka.filters.supervised.instance.SMOTE",
                    options=[
                        '-K', str(n),
                        '-P', str(smote_factor)
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

            # Fill the information to the last result dictionary
            self.context["pp_filter"]["strategy"] = "SMOTE"
            self.context["pp_filter"]["neighbors"] = n
            self.context["pp_filter"]["factor"] = smote_factor

        else:
            raise ValueError("Unknown strategy: {}".format(self.pp_strat))

        return filters
    # End def _build_pp_filters

# End class Learner


# ===== ( Module private functions ) ===================================================================================

def _get_stats_from_evaluator(evl, classes):
    evaluator_stats = dict()
    summary = evl.summary().split("\n")
    details = evl.class_details().split("\n")
    for s in summary:
        if "Correctly Classified Instances" in s:
            evaluator_stats["correctly_classified"] = float(s.split()[3])
        if "Incorrectly Classified Instances" in s:
            evaluator_stats["incorrectly_classified"] = float(s.split()[3])
        if "Total Number of Instance" in s:
            evaluator_stats["total_num_instances"] = float(s.split()[-1])

    for d in details:
        d = d.split()
        if len(d) > 0 and d[-1] in classes:
            evaluator_stats[d[-1]] = dict()
            evaluator_stats[d[-1]]["tp_rate"] = float(d[0]) if d[0] != "?" else 0
            evaluator_stats[d[-1]]["fp_rate"] = float(d[1]) if d[1] != "?" else 0
            evaluator_stats[d[-1]]["precision"] = float(d[2]) if d[2] != "?" else 0
            evaluator_stats[d[-1]]["recall"] = float(d[3]) if d[3] != "?" else 0
            evaluator_stats[d[-1]]["f_measure"] = float(d[4]) if d[4] != "?" else 0
            evaluator_stats[d[-1]]["mcc"] = float(d[5]) if d[5] != "?" else 0
            evaluator_stats[d[-1]]["roc"] = float(d[6]) if d[6] != "?" else 0
            evaluator_stats[d[-1]]["prc"] = float(d[7]) if d[7] != "?" else 0

    return evaluator_stats
# End def extract_evaluator_stats
