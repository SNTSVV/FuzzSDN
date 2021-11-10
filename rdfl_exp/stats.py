import json

from rdfl_exp.machine_learning.rule import RuleSet


class Stats:

    _stats = None
    
    @classmethod
    def init(cls, context: dict):
        cls._stats = cls._create_stats_dict(context["target_class"], context["other_class"])
        cls._stats["context"]["ml_algorithm"]           = context["ml_algorithm"].upper()
        cls._stats["context"]["pp_strategy"]            = context["pp_strategy"].lower()
        cls._stats["context"]["iteration_limit"]        = context["it_max"]
        cls._stats["context"]["samples_per_iteration"]  = context["nb_of_samples"]
    # End def __init__

    @classmethod
    def save(cls, path: str):
        """
        Save the statistics to a file.
        :param path: The os path to the statistic file
        """
        with open(path, 'w') as stats_file:
            json.dump(cls._stats, stats_file)
    # End def save

    @classmethod
    def add_iteration_statistics(cls, learning_time, iteration_time, clsf_res, rule_set : RuleSet):

        # List the classes
        classes = (cls._stats["context"]["target_class"],
                   cls._stats["context"]["other_class"])

        # Increment the number of iterations
        cls._stats["context"]["iterations"] += 1

        # Add the new timings
        cls._stats["timing"]["learning"]    += [str(learning_time)]
        cls._stats["timing"]["iteration"]   += [str(iteration_time)]

        # Update the classifier results
        cls._stats["classifier"]["instances"]  += [clsf_res['total_num_instances']]
        cls._stats["classifier"]["accuracy"]   += [clsf_res['correctly_classified'] / clsf_res['total_num_instances']]
        cls._stats["classifier"]["confidence"] += [rule_set.confidence()]
        cls._stats["classifier"]["rules"]      += [[str(r) for r in rule_set]]

        for class_ in classes:
            if class_ in clsf_res:
                cls._stats["classifier"][class_]["tp_rate"]            += [clsf_res[class_]['tp_rate']]
                cls._stats["classifier"][class_]["fp_rate"]            += [clsf_res[class_]['fp_rate']]
                cls._stats["classifier"][class_]["precision"]          += [clsf_res[class_]['precision']]
                cls._stats["classifier"][class_]["recall"]             += [clsf_res[class_]['recall']]
                cls._stats["classifier"][class_]["f_measure"]          += [clsf_res[class_]['f_measure']]
                cls._stats["classifier"][class_]["mcc"]                += [clsf_res[class_]['mcc']]
                cls._stats["classifier"][class_]["roc"]                += [clsf_res[class_]['roc']]
                cls._stats["classifier"][class_]["prc"]                += [clsf_res[class_]['prc']]
    # End def add_iteration_statistics

    # ====== ( create the dict ) ===========================================================================================

    @classmethod
    def _create_stats_dict(cls, target_class: str, other_class: str) -> dict:
        """
        Create the dictionary used by the stats class to generate
        :param target_class: The class that is the target of the prediction
        :param other_class:  The other class of the classifier
        :return: An empty statistics dictionnary
        """
        stats = dict()

        stats["context"]                                = dict()
        stats["context"]["pid"]                         = str()
        stats["context"]["iteration_limit"]             = int()
        stats["context"]["iterations"]                  = int()
        stats["context"]["ml_algorithm"]                = str()
        stats["context"]["pp_strategy"]                 = str()
        stats["context"]["target_class"]                = target_class
        stats["context"]["other_class"]                 = other_class

        stats["timing"]                                 = dict()
        stats["timing"]["learning"]                     = list()
        stats["timing"]["iteration"]                    = list()

        stats["classifier"]                             = dict()
        stats["classifier"]["instances"]                = list()
        stats["classifier"]["accuracy"]                 = list()
        stats["classifier"]["confidence"]               = list()
        stats["classifier"]["rules"]                    = list()

        for class_ in (target_class, other_class):
            stats["classifier"][class_]                 = dict()
            stats["classifier"][class_]["tp_rate"]      = list()
            stats["classifier"][class_]["fp_rate"]      = list()
            stats["classifier"][class_]["precision"]    = list()
            stats["classifier"][class_]["recall"]       = list()
            stats["classifier"][class_]["f_measure"]    = list()
            stats["classifier"][class_]["mcc"]          = list()
            stats["classifier"][class_]["roc"]          = list()
            stats["classifier"][class_]["prc"]          = list()

        return stats
    # End def _create_stats_dict
# End class Stats