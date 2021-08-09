import re

from weka.classifiers import Classifier, Evaluation
from weka.core.classes import Random
from weka.core.converters import Loader

from rdfl_exp.machine_learning.rule import Rule, Rule
import logging

log = logging.getLogger("ML algorithm")

def standard(data_path, tt_split=66.0, cv_folds=None, seed=1, classes=('1', '2')):
    """
    Perform a feature selection +
    :param classes:
    :param cv_folds:
    :param data_path:
    :param tt_split:
    :param seed:
    :return:
    """

    # load data from arff file
    log.info("Loading data from {}".format(data_path))
    loader = Loader("weka.core.converters.ArffLoader")
    data = loader.load_file(data_path)
    data.class_is_last()

    # generate train/test split of randomized data
    log.info("Splitting train and test data with ratio {}%".format(tt_split))
    train, test = data.train_test_split(tt_split, Random(seed))

    # build classifier
    print("Building the classifier")
    log.info("Building the classifier")
    cls = Classifier(classname="weka.classifiers.rules.JRip")
    cls.build_classifier(train)
    log.info(cls)

    # evaluate and record predictions in memory
    print("Evaluating the classifier")
    log.info("Evaluating the classifier")
    evl = Evaluation(train)

    # If cv_folds > 0, perform cross validation
    if cv_folds:
        if not isinstance(cv_folds, int) or cv_folds < 1:
            ValueError("Argument \"cv_folds\" must be None or an integer >= 1 (not \"{}\")".format(cv_folds))
        evl.crossvalidate_model(cls, data, cv_folds, Random(seed))
    else:
        evl.test_model(cls, test)
    # print(evl.summary())

    # Extract the rules
    rules = extract_rules_from_classifier(cls)

    return rules, extract_evaluator_stats(evl, classes=classes)
# End def standard


def extract_rules_from_classifier(cls):

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


def extract_evaluator_stats(evl, classes):

    evaluator_stats = dict()
    summary = evl.summary().split("\n")
    details = evl.class_details().split("\n")
    for s in summary:
        if "Correctly Classified Instances" in s:
            evaluator_stats["correctly_classified"] = int(s.split()[3])
        if "Incorrectly Classified Instances" in s:
            evaluator_stats["incorrectly_classified"] = int(s.split()[3])
        if "Total Number of Instance" in s:
            evaluator_stats["total_num_instances"] = int(s.split()[-1])

    for d in details:
        d = d.split()
        if len(d) > 0 and d[-1] in classes:
            evaluator_stats[d[-1]] = dict()
            evaluator_stats[d[-1]]["tp_rate"]   = float(d[0]) if d[0] != "?" else 0
            evaluator_stats[d[-1]]["fp_rate"]   = float(d[1]) if d[1] != "?" else 0
            evaluator_stats[d[-1]]["precision"] = float(d[2]) if d[2] != "?" else 0
            evaluator_stats[d[-1]]["recall"]    = float(d[3]) if d[3] != "?" else 0
            evaluator_stats[d[-1]]["f_measure"] = float(d[4]) if d[4] != "?" else 0
            evaluator_stats[d[-1]]["mcc"]       = float(d[5]) if d[5] != "?" else 0
            evaluator_stats[d[-1]]["roc"]       = float(d[6]) if d[6] != "?" else 0
            evaluator_stats[d[-1]]["prc"]       = float(d[7]) if d[7] != "?" else 0

    return evaluator_stats
