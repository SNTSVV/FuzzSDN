import base64
import json
import logging
import os
from collections import Counter
from copy import copy
from typing import Optional

import pandas as pd
from pypika import Column, JoinType, Query, Tables

from rdfl_exp.analytics.log import LogParser, OnosLogParser, RyuLogParser
from rdfl_exp.config import DEFAULT_CONFIG as CONFIG
from rdfl_exp.experiment import RuleSet
from rdfl_exp.setup import LOG_TRACE_DIR
from rdfl_exp.utils.metrics import imbalance_ratio, geometric_diversity, fraction_of_borderline_points
from rdfl_exp.utils.database import Database as SqlDb

DB_NAME = "rdfl_exp"


class Analyzer:

    def __init__(self):
        self.__log = logging.getLogger(__name__)

        # Analytics
        self.__controller   : Optional[str] = None
        self.__log_parser   : Optional[LogParser] = None

        # Counters
        self.__sample_cnt   = -1  # Counts the samples. Starts at -1 so it's 0 at the first iteration
        self.__it_cnt       = -1  # Counts the framework iteration. Starts at -1 so it's 0 at the first iteration

        # Flags
        self.__sample_table_created     = False
        self.__log_table_created        = False
        self.__rules_table_created      = False
        self.__current_it_has_ruleset   = False

        # Init the SQL database object if needed
        try:
            if not SqlDb.is_init():
                self.__log.info("Initializing the SQL database...")
                SqlDb.init(
                    hostname=CONFIG.mysql.host,
                    username=CONFIG.mysql.user,
                    password=CONFIG.mysql.password)
                self.__log.debug("The SQL database has been initialized successfully")
        finally:
            if SqlDb.is_init() is False:
                self.__log.error("An issue happened while initializing the database.")
    # End def __init__

    # ===== ( Properties ) =============================================================================================

    @property
    def controller(self):
        return copy(self.__controller)
    # End def controller

    @controller.setter
    def controller(self, value: str):
        """
        Sets the target controller
        :param value:
        :return:
        """
        allowed_controllers = ('onos', 'ryu')

        if value.lower() == 'onos':
            self.__controller = 'onos'
            self.__log_parser = OnosLogParser()

        elif value.lower() == 'ryu':
            self.__controller = 'ryu'
            self.__log_parser = RyuLogParser()

        else:
            raise AttributeError("Unknown controller \"{}\". Supported controllers are: {}".format(value, ','.join(
                '\"{}\"'.format(c) for c in allowed_controllers)))
    # End def controller.setter

    # ===== ( Getters ) ================================================================================================

    def get_dataset(self, iteration=None, error_class=None, debug=False) -> pd.DataFrame:
        """
        Outputs the analyzed dataset as a Pandas' dataframe.

        :param iteration: Output the dataset of a given iteration. If set to None, the whole dataset is output.
        :param error_class: Parse the dataset according to the error class. If set to None, no error class is inferred.
        :param debug: whether or not to output debug information

        :return: a pd.DataFrame
        """
        # Get the latest available dataset
        # query: FROM `samples` SELECT samples.*, log.* JOIN `logs` ON samples.id == log.log_id
        samples, rules, logs = Tables('samples', 'rules', 'logs')
        stmt = Query \
            .from_(samples) \
            .join(logs, how=JoinType.left) \
            .on(samples.sample_id == logs.log_id) \

        if debug is True:
            stmt = stmt.join(rules, how=JoinType.left).on(samples.rule_id == rules.rule_id)
            stmt = stmt.select(samples.star,
                               rules.expression,
                               rules.classification,
                               rules.coverage,
                               rules.misclassified,
                               logs.has_error,
                               logs.error_type,
                               logs.error_reason,
                               logs.error_effect)
        else:
            stmt = stmt.select(samples.star,
                               logs.has_error,
                               logs.error_type,
                               logs.error_reason,
                               logs.error_effect)

        if iteration is not None:
            stmt = stmt.where(samples.iter_id <= iteration)

        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)

            SqlDb.execute(stmt.get_sql(quote_char=None))
            SqlDb.commit()

            # Catch the field names and data
            field_names = [c[0] for c in SqlDb.get_cursor().description]
            data = SqlDb.fetchall()
        except Exception as e:
            raise e
        finally:
            SqlDb.disconnect()

        # Transform the SQL data to a pandas dataframe and drop the unused columns
        df = pd.DataFrame(data, columns=field_names)
        if not debug:
            df.drop(
                [
                    'sample_id',
                    'seq_id',
                    'iter_id',
                    'log_id',
                    'rule_id'
                ],
                axis='columns',
                inplace=True,
                errors='ignore'
            )

        # Transform the has_error column into boolean values
        df['has_error'] = df['has_error'].apply(lambda x: x == b'\x01')

        if error_class is not None:
            # OFPBAC_BAD_OUT_PORT
            if error_class == 'OFPBAC_BAD_OUT_PORT':
                if self.__controller == 'ryu':
                    df['class'] = df['error_reason'].apply(
                        lambda row: "OFPBAC_BAD_OUT_PORT" if row == "OFPBAC_BAD_OUT_PORT" else "OTHER_REASON")

                elif self.__controller == 'onos':
                    df['class'] = df.error_reason.apply(
                        lambda row: "OFPBAC_BAD_OUT_PORT" if 'BAD_OUT_PORT' in row else "OTHER_REASON"
                    )

            # Unknown Reason / Known Reason
            elif error_class in ('unknown_reason', 'known_reason'):
                if self.__controller == 'onos':
                    df['class'] = df.apply(
                        lambda row: 'unknown_reason' if row.has_error is True and row.error_reason is None else 'known_reason',
                        axis='columns'
                    )
                elif self.__controller == 'ryu':
                    df['class'] = df.apply(
                        lambda row: 'unknown_reason' if row.error_reason is None else 'known_reason',
                        axis='columns'
                    )
            # Parsing / Non parsing error
            elif error_class in ('parsing_error', 'non_parsing_error'):
                df['class'] = df['error_reason'].apply(
                    lambda row: "parsing_error" if row == "PARSING_ERROR" else "non_parsing_error")

            # Unknown Target Error
            else:
                raise ValueError("Unknown target error '{}'".format(error_class))

            # Drop the error-related columns
            if not debug:
                df.drop(
                    [
                        'has_error',
                        'error_type',
                        'error_reason',
                        'error_effect'
                    ],
                    axis='columns',
                    inplace=True,
                    errors='ignore'
                )

        return df
    # End def get_data

    def get_dataset_metrics(self, iteration=None, error_class=None):
        """
        Calculate the imbalance ratio at iteration X
        :param iteration:
        :param error_class:
        :return: a {dict} of the metrics
        """
        data = self.get_dataset(iteration=iteration, error_class=error_class, debug=False)

        # Extract the feature vector and the target vector
        X = data.drop(columns=['class']).values
        y = data['class'].values

        self.__log.trace("Computing Imbalance Ratio...")
        ir_score = imbalance_ratio(X, y)
        self.__log.trace("Done. IR = {}".format(ir_score))
        self.__log.trace("Computing Geometric Diversity...")
        gd_score = geometric_diversity(X)
        self.__log.trace("Done. IR = {}".format(gd_score))
        self.__log.trace("Computing N1 score...")
        n1_score = fraction_of_borderline_points(X, y)
        self.__log.trace("Done. IR = {}".format(n1_score))

        metrics = {
            'instances': Counter(y),
            'ir_score' : ir_score,
            'gd_score' : gd_score,
            'n1_score' : n1_score
        }

        return metrics
    # End def get_metrics

    # ===== ( Setters ) ================================================================================================

    def set_ruleset_for_iteration(self, ruleset : RuleSet):

        # Create the rule table if necessary
        if self.__rules_table_created is False:
            self.__create_rules_table()

        # Ignore this step if some rules where already set for this ruleset
        if self.__current_it_has_ruleset is True:
            self.__log.warning("Tried to add another ruleset for the current iteration. The instruction was ignored.")
            return

        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)

            for rule in ruleset:
                stmt = Query.into("rules").insert(
                        rule.id,            # rule_id
                        self.__it_cnt,      # iter_id
                        str(rule.expr),     # expr
                        rule.class_,        # class
                        rule.coverage,      # coverage
                        rule.misclassified  # misclassified)
                    )
                SqlDb.execute(stmt.get_sql(quote_char=None))

            # Commit all the statements at the same time
            SqlDb.commit()

        except Exception as e:
            raise e

        finally:
            SqlDb.disconnect()
    # End def set_ruleset_for_iteration

    # ===== ( Analysis ) ===============================================================================================

    def new_iteration(self):
        """
        Notifies the analyzer that there is a new transaction
        :return:
        """
        self.__it_cnt += 1
        self.__current_it_has_ruleset = False
    # End def new_iteration

    def start_analysis(self):
        self.__sample_cnt += 1
    # End def start_analysis

    def finish_analysis(self):
        """
        Finish the analysis of the current transaction

        :return:
        """
        # TODO: take into account, the fact that there could be many different packets fuzzed
        # Read the fuzzer report
        pkt_struct, pkt_values, pkt_actions = self.__read_fuzz_report()

        log_parse_results = self.__log_parser.parse_log()

        # Save the log_trace:
        with open(os.path.join(LOG_TRACE_DIR, 'log_trace_{}.log'.format(self.__sample_cnt)), 'w') as f:
            f.write(log_parse_results[4])

        # Create the samples and log table if required
        if self.__sample_table_created is False:
            self.__create_sample_table_from_packet_struct(pkt_struct)

        if self.__log_table_created is False:
            self.__create_logs_table()

        if self.__rules_table_created is False:
            self.__create_rules_table()

        # Insert the table result into the database
        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)

            # Determine if a rule should be added
            rule_id = None
            for pkt_action in pkt_actions:
                if pkt_action['action']['intent'] == 'mutate_packet_rule':
                    rule_id = int(pkt_action['action']['ruleID'])
                    break  # break out of the loop

            # First add the samples
            # NOTE: For now, the seq_id is equal to the sample_id but it is planned in the future that a seq_id could be
            #       given to several samples part of a same sequence
            stmt_1 = Query.into("samples").insert(
                self.__sample_cnt,                                      # sample_id
                self.__sample_cnt,                                      # seq_id
                self.__it_cnt,                                          # iter_id
                rule_id,                                                # rule_id
                *(pkt_values.get(k, None) for k in pkt_values.keys())   # fields_data
            )

            # Then add the logs
            # NOTE: For now, the log_id has the same value as the sample_count, but this should be different.
            stmt_2 = Query.into("logs").insert(self.__sample_cnt,                           # log_id
                                               self.__it_cnt,                               # iter_id
                                               1 if log_parse_results[0] is True else 0,    # has_error
                                               log_parse_results[1],                        # error_type
                                               log_parse_results[2],                        # error_reason
                                               log_parse_results[3])                        # error_effect

            # Execute the two queries
            SqlDb.execute(stmt_1.get_sql(quote_char=None))
            SqlDb.execute(stmt_2.get_sql(quote_char=None))
            SqlDb.commit()
        except Exception as e:
            raise e
        finally:
            SqlDb.disconnect()
    # End def finish_analysis

    # ===== ( Private Methods ) ========================================================================================

    # TODO: Parse actions and the mutations
    @staticmethod
    def __read_fuzz_report():

        report_path = os.path.expanduser(CONFIG.fuzzer.out_path)
        with open(report_path, 'r') as f:
            data = json.load(f)

        # Get the packet structure, sorted by offset
        pkt_struct = sorted(data['packetStruct']['fields'], key=lambda d: d['offset'])
        # Get the fuzzed packet
        fuzzed_packet = base64.b64decode(data['finalPacket'])

        pkt_values = dict()
        # Get each field and the associated value, stores it in a
        for field in pkt_struct:
            value = int.from_bytes(fuzzed_packet[field['offset']: field['offset'] + field['length']], byteorder='big')
            if 'mask' in field.keys():
                mask_copy = copy(field['mask'])
                mtz = 0
                while (mask_copy & 1) == 0:
                    mask_copy >>= 1
                    mtz += 1
                value &= field['mask']
                value >>= mtz
            # Store the value in the pkt_fields dictionary
            pkt_values[field['name']] = value

        return pkt_struct, pkt_values, data['fuzzActions']
    # End def __read_fuzz_report

    def __create_sample_table_from_packet_struct(self, pkt_struct):
        """
        Create the
        :param pkt_struct:
        :return:
        """
        pkt_fields_length   = [(f['name'], f['length']) for f in pkt_struct]
        sql_sample_cols = list()

        for field, length in pkt_fields_length:
            # Determine the type according to the fields length
            if length <= 1:
                type_ = 'TINYINT UNSIGNED'
            elif length <= 2:
                type_ = 'SMALLINT UNSIGNED'
            elif length <= 4:
                type_ = 'INT UNSIGNED'
            elif length <= 8:
                type_ = 'BIGINT UNSIGNED'
            else:
                # FIXME: Find alternative for very long integers
                msg = "Length of field \"{}\" is to big for storing it in a SQL database (got: {} > 8)".format(field, length)
                self.__log.error(msg)
                raise AttributeError(msg)
            # Add the column to the table
            sql_sample_cols.append(Column(field, type_))

        stmt = Query \
            .create_table("samples") \
            .columns(
                Column("sample_id"  , 'INT', nullable=False),
                Column("seq_id"     , 'INT', nullable=False),
                Column("iter_id"    , 'INT', nullable=False),
                Column("rule_id"    , 'INT', nullable=True),
                *sql_sample_cols) \
            .unique("sample_id", "iter_id") \
            .primary_key("sample_id")

        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)

            # Clear
            SqlDb.execute('DROP TABLE IF EXISTS `samples`')  # Drop the table if it exists
            SqlDb.execute(stmt.get_sql(quote_char=None))  # Create the table
            SqlDb.commit()
            self.__log.debug("SQL database has been cleaned.")
            self.__sample_table_created = True

        finally:
            SqlDb.disconnect()
    # End def __create_sample_table_from_packet_strut

    def __create_logs_table(self):
        """
        Create the log analysis table
        """
        stmt = Query \
            .create_table("logs") \
            .columns(
                Column("log_id"         , 'INT UNSIGNED', nullable=False),
                Column('iter_id'        , 'INT UNSIGNED', nullable=False),
                Column("has_error"      , 'BIT(1)'      , nullable=False),
                Column('error_type'     , 'VARCHAR(255)', nullable=True),
                Column('error_reason'   , 'VARCHAR(255)', nullable=True),
                Column('error_effect'   , 'VARCHAR(255)', nullable=True)) \
            .unique("log_id") \
            .primary_key("log_id")

        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)

            self.__log.info("Clearing the SQL database...")

            # Clear
            SqlDb.execute('DROP TABLE IF EXISTS `logs`')  # Drop the table if it exists
            SqlDb.execute(stmt.get_sql(quote_char=None))  # Create the table
            SqlDb.commit()

            self.__log.debug("SQL database has been cleaned.")
            self.__log_table_created = True

        finally:
            SqlDb.disconnect()
    # End def __create_log_table

    def __create_rules_table(self):
        """
        Create the log analysis table
        """
        stmt = Query \
            .create_table("rules") \
            .columns(
                Column("rule_id"        , 'BIGINT'      , nullable=False),
                Column("iter_id"        , 'BIGINT'      , nullable=False),
                Column("expression"     , 'TEXT'        , nullable=False),
                Column('classification' , 'VARCHAR(255)', nullable=False),
                Column('coverage'       , 'INT UNSIGNED', nullable=False),
                Column('misclassified'  , 'INT UNSIGNED', nullable=False)) \
            .unique("rule_id") \
            .primary_key("rule_id")

        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)

            self.__log.info("Clearing the SQL database...")

            # Clear
            SqlDb.execute('DROP TABLE IF EXISTS `rules`')  # Drop the table if it exists
            SqlDb.execute(stmt.get_sql(quote_char=None))  # Create the table
            SqlDb.commit()

            self.__log.debug("SQL database has been cleaned.")
            self.__rules_table_created = True

        finally:
            SqlDb.disconnect()
    # End def __create_rules_table

# End class Analyzer
