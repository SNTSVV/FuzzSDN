import re

from weka.classifiers import Classifier, Evaluation
from weka.core.classes import Random
from weka.core.converters import Loader

import rdfl_exp.machine_learning.rule as ml_rule


def standard(data_path, tt_split=66.0, cv_folds=None, seed=1):
    """
    Perform a feature selection +
    :param cv_folds:
    :param data_path:
    :param tt_split:
    :param seed:
    :return:
    """

    # load data from arff file
    print("Loading data from {}".format(data_path))
    loader = Loader("weka.core.converters.ArffLoader")
    data = loader.load_file(data_path)
    data.class_is_last()

    # generate train/test split of randomized data
    print("Splitting train and test data with ration {}%".format(tt_split))
    train, test = data.train_test_split(tt_split, Random(seed))

    # build classifier
    print("Building classifier")
    cls = Classifier(classname="weka.classifiers.rules.JRip")
    cls.build_classifier(train)
    print(cls)

    # evaluate and record predictions in memory
    print("Evaluating the classifier")
    evl = Evaluation(train)

    # If cv_folds > 0, perform cross validation
    if cv_folds:
        if not isinstance(cv_folds, int) or cv_folds < 1:
            ValueError("Argument \"cv_folds\" must be None or an integer >= 1 (not \"{}\")".format(cv_folds))
        evl.crossvalidate_model(cls, data, cv_folds, Random(seed))
    else:
        evl.test_model(cls, test)
    # print(evl.summary())

    # Get the precision
    precision = evl.precision(1)
    recall = evl.recall(1)

    # Extract the rules
    rules = extract_rules_from_classifier(cls)

    return rules, precision, recall
# End def standard


def extract_rules_from_classifier(cls):

    rules = []
    lines = cls.__str__().split("\n")
    for line in lines:
        # Check if the line match the structure of a rule
        if re.match(r'(.*)=>(.*=.*\(.*/.*\))', line):
            rules.append(ml_rule.from_string(line))

    return rules
# End def extract_rules_from_classifier
