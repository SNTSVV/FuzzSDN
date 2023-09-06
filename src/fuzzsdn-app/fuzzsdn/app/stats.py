import json
from typing import Optional

from fuzzsdn.app.experiment import Learner, Model


class Stats:

    _stats = None
    
    @classmethod
    def init(cls, context: dict):
        cls._stats = cls._create_stats_dict()

        cls._stats['context']['scenario']               = context['scenario']
        cls._stats['context']['criterion']              = context['criterion']
        cls._stats['context']['fut']                    = context['fut']
        cls._stats['context']['method']                 = context['method']
        cls._stats['context']['algorithm']              = context['algorithm']
        cls._stats['context']['filter']                 = context['filter']
        cls._stats['context']['it_limit']               = context['it_limit']
        cls._stats['context']['time_limit']             = context['time_limit']
        cls._stats['context']['samples_per_iteration']  = context['nb_of_samples']
        cls._stats['context']['mutation_rate']          = context['mutation_rate']
    # End def __init__

    @classmethod
    def save(cls, path: str, pretty : bool = False):
        """
        Save the statistics to a file.

        Args:
            path (bool): The os path to the statistic file
            pretty (bool): Save in a pretty format, indented, and sorted by keys
        """
        with open(path, 'w') as stats_file:
            if pretty is True:
                json.dump(cls._stats, stats_file, indent=4, sort_keys=True)
            else:
                json.dump(cls._stats, stats_file)
    # End def save

    @classmethod
    def add_iteration_statistics(
            cls,
            testing_time,
            fuzzing_time,
            learning_time,
            planning_time,
            iteration_time,
            learner : Learner,
            model: Optional[Model]
    ):
        # List the classes
        target_class, other_class = cls._stats["context"]["target_class"], cls._stats["context"]["other_class"]

        # Increment the number of iterations
        cls._stats["context"]["iterations"] += 1

        # Add the new timings
        cls._stats["timing"]["learning"]    += [float(learning_time)]
        cls._stats["timing"]["iteration"]   += [float(iteration_time)]
        cls._stats['timing']['testing']     += [float(testing_time)]
        cls._stats['timing']['planning']    += [float(planning_time)]
        cls._stats['timing']['fuzzing']     += [float(fuzzing_time)]

        # Add the information about the data
        count = learner.get_instances_count()
        cls._stats['data']['count']['all']          += [count['all']]
        cls._stats['data']['count'][target_class]   += [count[target_class]]
        cls._stats['data']['count'][other_class]    += [count[other_class]]

        # Update the machine learning results
        if model is not None:
            cls._stats['learning']['scheme']    += [model.info.scheme]
            cls._stats['learning']["accuracy"]  += [model.info.accuracy]
        else:
            cls._stats['learning']['scheme']    += [None]
            cls._stats['learning']["accuracy"]  += [None]

        if model is not None and model.ruleset is not None:
            cls._stats['learning']['confidence'] += [model.ruleset.confidence()]
        else:
            cls._stats['learning']['confidence'] += [None]

        # Add the rules and their statistics at each iteration
        rules_info = list()
        try:
            for i in range(len(model.ruleset)):
                rule_dict = dict()
                rule_dict['id']                     = model.ruleset[i].id
                rule_dict['class']                  = model.ruleset[i].get_class()
                rule_dict['support']                = model.ruleset.support(i)
                rule_dict['confidence']             = model.ruleset.confidence(i, relative=False)
                rule_dict['relative_confidence']    = model.ruleset.confidence(i, relative=True)
                rule_dict['budget']                 = model.ruleset[i].get_budget()
                rule_dict['repr']                   = str(model.ruleset[i])
                rules_info += [rule_dict]
        except (TypeError, AttributeError):
            # Then rule_set is empty
            rules_info = None
        finally:
            cls._stats['learning']['rules']   += [rules_info]

        for class_ in (target_class, other_class):
            if model is not None and class_ in model.info.classes:
                cls._stats['learning'][class_]['num_tp']    += [model.info.num_tp[class_]]
                cls._stats['learning'][class_]['num_fp']    += [model.info.num_fp[class_]]
                cls._stats['learning'][class_]['num_tn']    += [model.info.num_tn[class_]]
                cls._stats['learning'][class_]['num_fn']    += [model.info.num_fn[class_]]
                cls._stats['learning'][class_]['precision'] += [model.info.precision[class_]]
                cls._stats['learning'][class_]['recall']    += [model.info.recall[class_]]
                cls._stats['learning'][class_]['f_measure'] += [model.info.f_measure[class_]]
                cls._stats['learning'][class_]['mcc']       += [model.info.mcc[class_]]
                cls._stats['learning'][class_]['auroc']     += [model.info.auroc[class_]]
                cls._stats['learning'][class_]['auprc']     += [model.info.auprc[class_]]
            else:
                cls._stats['learning'][class_]['num_tp']    += [None]
                cls._stats['learning'][class_]['num_fp']    += [None]
                cls._stats['learning'][class_]['num_tn']    += [None]
                cls._stats['learning'][class_]['num_fn']    += [None]
                cls._stats['learning'][class_]['precision'] += [None]
                cls._stats['learning'][class_]['recall']    += [None]
                cls._stats['learning'][class_]['f_measure'] += [None]
                cls._stats['learning'][class_]['mcc']       += [None]
                cls._stats['learning'][class_]['auroc']     += [None]
                cls._stats['learning'][class_]['auprc']     += [None]
    # End def add_iteration_statistics

    # ====== ( create the dict ) ===========================================================================================

    @classmethod
    def _create_stats_dict(cls) -> dict:
        """Create the dictionary used by the stats class to generate

        Returns:
            The dictionary used to store statistics.
        """
        stats = dict()

        # Information on the context
        stats['context']                                = dict()
        stats['context']['scenario']                    = str()
        stats['context']['criterion']                   = dict()
        stats['context']['fut']                         = str()
        stats['context']['method']                      = str()
        stats['context']['criterion']['name']           = str()
        stats['context']['criterion']['kwargs']         = dict()
        stats['context']['it_limit']                    = None
        stats['context']['time_limit']                  = None
        stats['context']['iterations']                  = int()
        stats['context']['algorithm']                   = str()
        stats['context']['filter']                      = str()
        stats['context']['target_class']                = 'FAIL'  # Always '''FAIL'''
        stats['context']['other_class']                 = 'PASS'  # and '''PASS'''

        # Information of the timing
        stats['timing']                                 = dict()
        stats['timing']['testing']                      = list()
        stats['timing']['fuzzing']                      = list()
        stats['timing']['planning']                     = list()
        stats['timing']['learning']                     = list()
        stats['timing']['iteration']                    = list()

        # Information on the data
        stats['data']                                   = dict()
        stats['data']['count']                          = dict()
        stats['data']['count']['all']                   = list()
        stats['data']['count']['FAIL']                  = list()
        stats['data']['count']['PASS']                  = list()

        # Information on the machine learning information
        stats['learning']                               = dict()
        stats['learning']['scheme']                     = list()
        stats['learning']['accuracy']                   = list()
        stats['learning']['confidence']                 = list()
        stats['learning']['rules']                      = list()
        stats['learning']['FAIL']                       = dict()
        stats['learning']['PASS']                       = dict()

        for class_ in ('FAIL', 'PASS'):
            stats['learning'][class_]["num_tp"]         = list()
            stats['learning'][class_]["num_fp"]         = list()
            stats['learning'][class_]["num_tn"]         = list()
            stats['learning'][class_]["num_fn"]         = list()
            stats['learning'][class_]["precision"]      = list()
            stats['learning'][class_]["recall"]         = list()
            stats['learning'][class_]["f_measure"]      = list()
            stats['learning'][class_]["mcc"]            = list()
            stats['learning'][class_]["auroc"]          = list()
            stats['learning'][class_]["auprc"]          = list()
        return stats
    # End def _create_stats_dict
# End class Stats
