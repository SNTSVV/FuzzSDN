import json

from rdfl_exp.experiment import Experimenter, Learner


class Stats:

    _stats = None
    
    @classmethod
    def init(cls, context: dict):
        cls._stats = cls._create_stats_dict(context["target_class"], context["other_class"])
        cls._stats['context']['scenario']               = context['scenario']
        cls._stats['context']['criterion']              = context['criterion']
        cls._stats['context']['ml_algorithm']           = context['ml_algorithm'].upper()
        cls._stats['context']['pp_strategy']            = context['pp_strategy'].lower()
        cls._stats['context']['iteration_limit']        = context['it_max']
        cls._stats['context']['samples_per_iteration']  = context['nb_of_samples']
        cls._stats['context']['enable_mutation']        = context['enable_mutation']
        cls._stats['context']['mutation_rate']          = context['mutation_rate']
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
    def add_iteration_statistics(cls, learning_time, iteration_time, experimenter: Experimenter, learner : Learner):

        ml_results  = learner.get_results()
        rule_set    = learner.get_rules()

        # List the classes
        classes = (cls._stats["context"]["target_class"],
                   cls._stats["context"]["other_class"])

        # Increment the number of iterations
        cls._stats["context"]["iterations"] += 1

        # Add the new timings
        cls._stats["timing"]["learning"]    += [str(learning_time)]
        cls._stats["timing"]["iteration"]   += [str(iteration_time)]

        # Add the learning context
        cls._stats['learning']['context'] += [learner.get_context()]

        # Add the learning data
        cls._stats['learning']['data']['total_count']   += [learner.get_dataset_size()]
        target_count, other_count = learner.get_size_of_classes()
        cls._stats['learning']['data']['target_count']  += [target_count]
        cls._stats['learning']['data']['other_count']   += [other_count]
        cls._stats['learning']['data']['class_ratio'] += [target_count / (target_count + other_count)]

        # Update the machine learning results
        cls._stats['learning']['results']["instances"]  += [ml_results['evaluation']['total_num_instances']]
        cls._stats['learning']['results']["accuracy"]   += [ml_results['evaluation']['correctly_classified'] / ml_results['evaluation']['total_num_instances']]
        cls._stats['learning']['results']['confidence'] += [rule_set.confidence()]

        # Add the rules and their statistics at each iteration
        rules_info = list()
        for i in range(len(rule_set)):
            rule_dict = dict()
            rule_dict['id']                     = rule_set[i].id
            rule_dict['class']                  = rule_set[i].get_class()
            rule_dict['support']                = rule_set.support(i)
            rule_dict['confidence']             = rule_set.confidence(i, relative=False)
            rule_dict['relative_confidence']    = rule_set.confidence(i, relative=True)
            rule_dict['budget']                 = rule_set[i].get_budget()
            rule_dict['repr']                   = str(rule_set[i])
            rules_info += [rule_dict]

        cls._stats['learning']['results']['rules']   += [rules_info]

        for evl_method in ('cross-validation', 'evaluation'):
            for class_ in classes:
                if class_ in ml_results[evl_method]:
                    cls._stats['learning']['results'][evl_method][class_]['fp_rate']     += [ml_results[evl_method][class_]['fp_rate']]
                    cls._stats['learning']['results'][evl_method][class_]['tp_rate']     += [ml_results[evl_method][class_]['tp_rate']]
                    cls._stats['learning']['results'][evl_method][class_]['precision']   += [ml_results[evl_method][class_]['precision']]
                    cls._stats['learning']['results'][evl_method][class_]['recall']      += [ml_results[evl_method][class_]['recall']]
                    cls._stats['learning']['results'][evl_method][class_]['f_measure']   += [ml_results[evl_method][class_]['f_measure']]
                    cls._stats['learning']['results'][evl_method][class_]['mcc']         += [ml_results[evl_method][class_]['mcc']]
                    cls._stats['learning']['results'][evl_method][class_]['roc']         += [ml_results[evl_method][class_]['roc']]
                    cls._stats['learning']['results'][evl_method][class_]['prc']         += [ml_results[evl_method][class_]['prc']]

    # End def add_iteration_statistics

    # ====== ( create the dict ) ===========================================================================================

    @classmethod
    def _create_stats_dict(cls, target_class: str, other_class: str) -> dict:
        """
        Create the dictionary used by the stats class to generate
        :param target_class: The class that is the target of the prediction
        :param other_class:  The other class of the classifier
        :return: An empty statistics dictionary
        """
        stats = dict()

        stats['context']                                = dict()
        stats['context']['scenario']                    = str()
        stats['context']['criterion']                   = dict()
        stats['context']['criterion']['name']           = str()
        stats['context']['criterion']['kwargs']         = dict()
        stats['context']["pid"]                         = str()
        stats['context']["iteration_limit"]             = int()
        stats['context']["iterations"]                  = int()
        stats['context']["ml_algorithm"]                = str()
        stats['context']["pp_strategy"]                 = str()
        stats['context']["target_class"]                = target_class
        stats['context']["other_class"]                 = other_class

        stats['timing']                                 = dict()
        stats['timing']['learning']                     = list()
        stats['timing']['iteration']                    = list()

        stats['learning']                               = dict()
        stats['learning']['context']                    = list()
        stats['learning']['data']                       = dict()
        stats['learning']['data']['total_count']        = list()
        stats['learning']['data']['target_count']       = list()
        stats['learning']['data']['other_count']        = list()
        stats['learning']['data']['class_ratio']        = list()
        stats['learning']['results']                    = dict()
        stats['learning']['results']['instances']       = list()
        stats['learning']['results']['accuracy']        = list()
        stats['learning']['results']['confidence']      = list()
        stats['learning']['results']['rules']           = list()

        stats['learning']['results'].update({'cross-validation': dict(), 'evaluation': dict()})
        for evl_method in ('cross-validation', 'evaluation'):
            stats['learning']['results'][evl_method].update({target_class: dict(), other_class: dict()})
            for class_ in (target_class, other_class):
                stats['learning']['results'][evl_method][class_]["tp_rate"]      = list()
                stats['learning']['results'][evl_method][class_]["fp_rate"]      = list()
                stats['learning']['results'][evl_method][class_]["precision"]    = list()
                stats['learning']['results'][evl_method][class_]["recall"]       = list()
                stats['learning']['results'][evl_method][class_]["f_measure"]    = list()
                stats['learning']['results'][evl_method][class_]["mcc"]          = list()
                stats['learning']['results'][evl_method][class_]["roc"]          = list()
                stats['learning']['results'][evl_method][class_]["prc"]          = list()

        return stats
    # End def _create_stats_dict
# End class Stats
