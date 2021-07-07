import re
import traceback

import machine_learning.rule as ml_rule
import weka.core.jvm as jvm
from weka.classifiers import Classifier, Evaluation
from weka.core.classes import Random
from weka.core.converters import Loader


def standard(data_path, tt_split=66.0, seed=1):
    """
    Perform a feature selection +
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


if __name__ == '__main__':

    try:
        jvm.start()
        rules = standard("/Users/raphael.ollando/OneDrive - University of Luxembourg/03 - Research Notes/20210621 - Data.arff",
                         tt_split=70,
                         seed=1234)
        for r in rules:
            print(r)
    except Exception as e:
        print(traceback.format_exc())
    finally:
        jvm.stop()
