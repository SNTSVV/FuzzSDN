import logging
import re
import traceback

from weka.classifiers import Classifier, Evaluation, FilteredClassifier
from weka.core import jvm
from weka.core.classes import Random, deepcopy
from weka.core.converters import Loader
from weka.filters import Filter, MultiFilter

from rdfl_exp.machine_learning.rule import Rule

_log = logging.getLogger(__name__)


# ===== ( Algorithms ) =================================================================================================

def learn(data_path, algorithm, preprocess_strategy=None, n_folds=10, seed=1, classes=('1', '2')):
    """
    :param data_path: The path to the dataset
    :param algorithm: the ML algorithm to use
    :param preprocess_strategy: The strategy to use on the data
    :param classes: the name of the classes to be classified
    :param n_folds: Number of fold to apply for cross_validation
    :param seed: The seed to use for the ML algorithm
    :return:
    """

    # load data from arff file
    _log.info("Loading data from {}".format(data_path))
    loader = Loader("weka.core.converters.ArffLoader")
    data = loader.load_file(data_path)
    data.class_is_last()
    ctx = dict()  # The learning context.

    # Copy the data into data that will be use for cross validation and training
    training_data = deepcopy(data)

    # Build the classifier
    print("Building classifier using \"{}\" algorithm".format(algorithm))
    _log.info("Building classifier using \"{}\" algorithm".format(algorithm))

    # Create the filter to balance the data
    _fltr = None
    if preprocess_strategy is not None and preprocess_strategy != '':
        try:
            pp_fltr = _build_pp_filters(preprocess_strategy, data, ctx=ctx)
            if len(pp_fltr) > 1:  # Multiple filters
                _fltr = MultiFilter()
                for f in pp_fltr:
                    _fltr.append(f)
            elif len(pp_fltr) == 1:  # One filter
                _fltr = pp_fltr[0]
            else:
                pass
        except ValueError as e:
            # A value error is risen only when the preprocess strategy is not known
            _log.error("Couldn't apply strategy {} with error \"{}\"".format(preprocess_strategy, str(e)))
            _log.warning("Machine learning will be performed without any data preprocessing.")

    # Create the classifier
    _clf = None
    if algorithm.upper() == 'RIPPER':
        _clf = Classifier(classname="weka.classifiers.rules.JRip")
        ctx['classifier'] = dict()
        ctx['classifier']['name'] = "RIPPER"

    else:
        raise ValueError("Classifying algorithm \"{}\" is not supported.".format(algorithm))

    # Create the final classifier
    if _fltr is None:
        clf = _clf
    else:
        clf = FilteredClassifier()
        clf.filter = _fltr
        clf.classifier = _clf

    # Perform cross validation on the dataset
    print("Performing classifier evaluation...")
    _log.info("Performing classifier evaluation...")
    cross_evl = Evaluation(data)
    # If cv_folds > 0, perform cross validation
    if not isinstance(n_folds, int) or n_folds < 1:
        ValueError("The number of cross-validation folds must be an integer >= 1 (got: \"{}\")".format(n_folds))

    cross_evl.crossvalidate_model(clf, data, n_folds, Random(seed))
    _log.debug("Evaluator:\n{}\n{}".format(cross_evl.summary(), cross_evl.class_details("Statistics:")))

    # Fill the context
    ctx["cross-validation"] = dict()
    ctx["cross-validation"]["folds"] = n_folds
    ctx["cross-validation"]["seed"] = seed

    # Build the classifier
    print("Building the classifier...")
    clf.build_classifier(data)
    build_evl = Evaluation(data)
    build_evl.test_model(clf, data)

    _log.debug("Classifier:\n{}".format(clf))

    # Extract the association rules from the classifier
    output = dict()
    output['rules']             = _extract_rules_from_classifier(clf)
    output['cross-validation']  = _extract_evaluator_stats(cross_evl, classes=classes)
    output['evaluation']        = _extract_evaluator_stats(build_evl, classes=classes)
    if ctx is not None:
        output['context']       = ctx

    return output
# End def learn

# ===== ( Classifying Method and Strategy ) ===========================================================================


# def _preprocess_data(strategy: str, dataset: Union[Instances, list[Instances]]) -> Union[Instances, list[Instances]]:
def _build_pp_filters(strategy, dataset, ctx: dict = None):
    """
    Perform some preprocessing on the data depending on the strategy defined.
    If a strategy is not implemented, an error will be risen.

    :param strategy (str): the strategy to be used to preprocess the data
    :return:
    """

    filters = []

    # Balancing the dataset using under sampling method
    if strategy.lower() == 'undersampling':
        print("Creating filter for \"{}\" strategy".format(strategy))
        _log.debug("Creating filter for \"{}\" strategy".format(strategy))
        filters.append(
            Filter(classname="weka.filters.supervised.instance.SpreadSubsample", options=["-M", "1.0"])
        )

        # Fill the context if there is one
        if ctx is not None:
            ctx["pp_filter"] = dict()
            ctx["pp_filter"]["strategy"] = "undersampling"
            ctx["pp_filter"]["target_ratio"] = 0.5

    # Balancing the dataset using w
    elif strategy.lower() == 'weight_balancing':
        print("Using \"{}\" data preprocessing strategy".format(strategy))
        _log.debug("Using \"{}\" data preprocessing strategy".format(strategy))
        filters.append(
            Filter(classname="weka.filters.supervised.instance.ClassBalancer", options=["-num-intervals", "10"])
        )

        # Fill the context if there is one
        if ctx is not None:
            ctx["pp_filter"] = dict()
            ctx["pp_filter"]["strategy"] = "weight_balancing"
            ctx["pp_filter"]["num-intervals"] = 10

    elif strategy.upper().startswith("SMOTE"):
        match = re.match(r'(?P<smote>SMOTE)-?(?P<n>\d*)?', strategy.upper())

        n = int(match.group("n")) if match.group("n") != '' else 5  # Number of neighbours to consider
        index_list = (str(i + 1) for i in range(dataset.class_index))

        class1_cnt, class2_cnt = 0, 0
        for data in dataset:
            if int(data.get_value(data.class_index)) == 0:
                class1_cnt += 1
            else:
                class2_cnt += 1

        smote_factor = 100 * (max(class1_cnt, class2_cnt) - min(class1_cnt, class2_cnt)) / min(class1_cnt, class2_cnt)

        print("Using \"SMOTE-{}\" data preprocessing strategy".format(n))
        _log.debug("Using \"SMOTE-{}\" data preprocessing strategy".format(n))

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

        # Fill the context if there is one
        if ctx is not None:
            ctx["pp_filter"] = dict()
            ctx["pp_filter"]["strategy"] = "SMOTE"
            ctx["pp_filter"]["neighbors"] = n
            ctx["pp_filter"]["factor"] = smote_factor

    # No strategy
    elif strategy.lower() == 'none':
        pass
    else:
        raise ValueError("Unknown strategy: {}".format(strategy.upper()))

    return filters
# End def _build_pp_filters


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
