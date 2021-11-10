import logging
import math
import re

from weka.classifiers import Classifier, Evaluation
from weka.core import jvm
from weka.core.classes import Random
from weka.core.converters import Loader
from weka.core.dataset import Instances
from weka.filters import Filter

from rdfl_exp.machine_learning.rule import Rule, RuleSet

_log = logging.getLogger(__name__)


# ===== ( Algorithms ) =================================================================================================

def learn(data_path, algorithm, preprocess_strategy=None, n_folds=10, seed=1, classes=('1', '2')):
    """
    :param algorithm:
    :param preprocess_strategy:
    :param classes:
    :param n_folds:
    :param data_path:
    :param seed:
    :return:
    """

    # load data from arff file
    _log.info("Loading data from {}".format(data_path))
    loader = Loader("weka.core.converters.ArffLoader")
    data = loader.load_file(data_path)
    data.class_is_last()

    # preprocess the data
    if preprocess_strategy is not None and preprocess_strategy != '':
        try:
            data = _preprocess_data(preprocess_strategy, data)
        except ValueError as e:
            # A value error is risen only when the preprocess strategy is not known
            _log.error("Couldn't apply strategy {} with error \"{}\"".format(preprocess_strategy, str(e)))
            _log.warning("Machine learning will be performed without any data preprocessing.")
    # End if

    return _classify(algorithm, data, n_folds, seed=seed, classes=classes)


# End def learn

# ===== ( Classifying Method and Strategy ) ===========================================================================


# def _preprocess_data(strategy: str, dataset: Union[Instances, list[Instances]]) -> Union[Instances, list[Instances]]:
def _preprocess_data(strategy, dataset):
    """
    Perform some preprocessing on the data depending on the strategy defined.
    If a strategy is not implemented, an error will be risen.

    :param strategy (str): the strategy to be used to preprocess the data
    :return:
    """

    # Balancing the dataset using oversampling method

    # Balancing the dataset using under sampling method
    if strategy.lower() == 'undersampling':
        print("Using \"{}\" data preprocessing strategy".format(strategy))
        _log.debug("Using \"{}\" data preprocessing strategy".format(strategy))
        pp_filter = Filter(classname="weka.filters.supervised.instance.SpreadSubsample", options=["-M", "1.0"])
        pp_filter.inputformat(dataset)
        dataset_filtered = pp_filter.filter(dataset)

    # Balancing the dataset using w
    elif strategy.lower() == 'weight_balancing':
        print("Using \"{}\" data preprocessing strategy".format(strategy))
        _log.debug("Using \"{}\" data preprocessing strategy".format(strategy))
        pp_filter = Filter(classname="weka.filters.supervised.instance.ClassBalancer", options=["-num-intervals", "10"])
        pp_filter.inputformat(dataset)
        dataset_filtered = pp_filter.filter(dataset)

    elif strategy.upper().startswith("SMOTE"):
        match = re.match(r'(?P<smote>SMOTE)-?(?P<n>\d*)?', strategy.upper())

        n = int(match.group("n")) if match.group("n") != '' else 5  # Number of neighbours to consider
        index_list = (str(i+1) for i in range(dataset.class_index))

        class1_cnt, class2_cnt = 0, 0
        for data in dataset:
            if int(data.get_value(data.class_index)) == 0:
                class1_cnt += 1
            else:
                class2_cnt += 1

        smote_factor = 100 * (max(class1_cnt, class2_cnt) - min(class1_cnt, class2_cnt)) / min(class1_cnt, class2_cnt)

        print("Using \"SMOTE-{}\" data preprocessing strategy".format(n))
        _log.debug("Using \"SMOTE-{}\" data preprocessing strategy".format(n))

        pp_filter = Filter(classname="weka.filters.supervised.instance.SMOTE",
                           options=['-K', str(n),
                                    '-P', str(smote_factor)])
        int_filter = Filter(classname="weka.filters.unsupervised.attribute.NumericTransform",
                            options=['-C', "java.lang.Math",
                                     '-M', "ceil",
                                     '-R', ','.join(index_list)])
        pp_filter.inputformat(dataset)
        int_filter.inputformat(dataset)
        dataset_filtered = pp_filter.filter(dataset)

        int_filter.inputformat(dataset_filtered)
        dataset_filtered = int_filter.filter(dataset_filtered)

    # No strategy
    elif strategy.lower() == 'none':
        dataset_filtered = dataset
    else:
        raise ValueError("Unknown strategy: {}".format(strategy.upper()))

    return dataset_filtered
# End def _preprocess_data


# def _classify(algorithm: str, dataset: Union[Instances, list[Instances]], n_folds: int = 1, seed: int = 1,
#               classes=('1', '2')) -> (object, object):
def _classify(algorithm, dataset, n_folds=1, seed=1, classes=('1', '2')):
    # Build the classifier
    print("Building classifier using \"{}\" algorithm".format(algorithm))
    _log.info("Building classifier using \"{}\" algorithm".format(algorithm))

    cls = None
    if algorithm.upper() == 'RIPPER':
        cls = Classifier(classname="weka.classifiers.rules.JRip")
    else:
        raise ValueError("Classifying algorithm \"{}\" is not supported.".format(algorithm))

    cls.build_classifier(dataset)
    _log.debug("Classifier:\n{}".format(cls))

    # Evaluate and record predictions in memory
    print("Performing classifier evaluation...")
    _log.info("Performing classifier evaluation...sad")
    evl = Evaluation(dataset)
    # If cv_folds > 0, perform cross validation
    if not isinstance(n_folds, int) or n_folds < 1:
        ValueError("The number of cross-validation folds must be an integer >= 1 (got: \"{}\")".format(n_folds))
    evl.crossvalidate_model(cls, dataset, n_folds, Random(seed))
    _log.debug("Evaluator:\n{}\n{}".format(evl.summary(), evl.class_details()))

    # Extract the association rules from the classifier
    rules = _extract_rules_from_classifier(cls)
    stats = _extract_evaluator_stats(evl, classes=classes)

    return rules, stats


# End def _classify


# ====== ( Helper functions ) ==========================================================================================

def _extract_rules_from_classifier(cls):
    rules = []
    lines = cls.__str__().split("\n")
    for line in lines:
        # Check if the line match the structure of a rule
        if re.match(r'(.*)=>(.*=.*\(.*/.*\))', line):
            rule = Rule.from_string(line)
            if rule is not None:
                rules.append(rule)
    return rules


# End def extract_rules_from_classifier


def _extract_evaluator_stats(evl, classes):
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
