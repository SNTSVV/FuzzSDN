import base64
import json
import logging
import os
from copy import copy
from typing import Optional

import pandas as pd
from pypika import Column, Query, Tables

from rdfl_exp.analytics.log import LogParser, OnosLogParser, RyuLogParser
from rdfl_exp.config import DEFAULT_CONFIG as CONFIG
from rdfl_exp.setup import LOG_TRACE_DIR
from rdfl_exp.utils.database import Database as SqlDb

DB_NAME = "rdfl_exp"


class Analyzer:

    def __init__(self):
        self.__log = logging.getLogger(__name__)

        # Analytics
        self.__controller: str = None
        self.__log_parser: Optional[LogParser] = None

        # Counters
        self.__sample_cnt   = -1  # Counts the samples. Starts at -1 so it's 0 at the first iteration
        self.__it_cnt       = -1  # Counts the framework iteration. Starts at -1 so it's 0 at the first iteration

        # Flags
        self.__db_init                      = False
        self.__sample_data_table_created    = False
        self.__log_analysis_table_created   = False

        # Init the SQL database object if needed
        try:
            if not SqlDb.is_init():
                self.__log.info("Initializing the SQL database...")
                SqlDb.init(
                    hostname=CONFIG.mysql.host,
                    username=CONFIG.mysql.user,
                    password=CONFIG.mysql.password)
                self.__log.debug("The SQL database has been initialized successfully")
                self.__db_init = True
        finally:
            if self.__db_init is False:
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

    def get_data(self, iteration=None, format_error=None) -> pd.DataFrame:
        """

        :param iteration:
        :param format_error:
        :return:
        """
        # Get the latest available dataset
        # query: FROM `samples_data` SELECT samples.*, log.* JOIN `log_analysis` ON samples_data.id == log.log_id
        sample, log = Tables('samples_data', 'log_analysis')
        stmt = Query \
            .from_(sample) \
            .join(log) \
            .on(sample.sample_id == log.log_id) \
            .select(sample.star, log.star)

        if iteration is not None:
            stmt = stmt.where(sample.iter_id <= iteration)

        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)
            self.__log.trace("SQL query: {}".format(stmt.get_sql(quote_char=None)))
            SqlDb.execute(stmt.get_sql(quote_char=None))
            SqlDb.commit()

            # Catch the field names and data
            field_names = [c[0] for c in SqlDb.get_cursor().description]
            data = SqlDb.fetchall()
        except Exception as e:
            raise e
        finally:
            SqlDb.disconnect()

        # Transform the SQL data to a pandas dataframe
        df = pd.DataFrame(data, columns=field_names)
        df.drop(
            [
                'sample_id',
                'seq_id',
                'iter_id',
                'log_id',
                'has_error'
            ],
            axis='columns',
            inplace=True,
            errors='ignore'
        )

        if format_error is not None:

            format_error_lambda_dict = {
                'OFPBAC_BAD_OUT_PORT'   : lambda x: "OFPBAC_BAD_OUT_PORT" if x == "OFPBAC_BAD_OUT_PORT" else "OTHER_REASON",

                'unknown_reason'        : lambda x: 'unknown_reason' if x is None else 'known_reason',
                'known_reason'          : lambda x: 'unknown_reason' if x is None else 'known_reason',

                'non_parsing_error'     : lambda x: "parsing_error" if x == "PARSING_ERROR" else "non_parsing_error",
                'parsing_error'         : lambda x: "parsing_error" if x == "PARSING_ERROR" else "non_parsing_error",
            }
            lambda_ = format_error_lambda_dict.get(format_error, None)

            if lambda_ is not None:
                df['class'] = df['error_reason'].apply(lambda_)
            else:
                raise ValueError("Unknown target error '{}'".format(format_error))

            # Drop the error columns
            df.drop(['error_type', 'error_reason', 'error_effect'], axis='columns', inplace=True, errors='ignore')

        return df
    # End def get_data

    # ===== ( Analyze ) ================================================================================================

    def new_iteration(self):
        """
        Notifies the analyzer that there is a new transaction
        :return:
        """
        self.__it_cnt += 1
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
        pkt_struct, fields, _ = self.__read_fuzz_report()

        log_parse_results = self.__log_parser.parse_log()

        # Save the log_trace:
        with open(os.path.join(LOG_TRACE_DIR, 'log_trace_{}.log'.format(self.__sample_cnt)), 'w') as f:
            f.write(log_parse_results[4])

        # Create the samples and log table if required
        if self.__sample_data_table_created is False:
            self.__create_sample_data_table_from_packet_struct(pkt_struct)

        if self.__log_analysis_table_created is False:
            self.__create_log_analysis_table()

        # Insert the table result into the database
        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)

            # First add the samples
            # NOTE: For now, the seq_id is equal to the sample_id but it is planned in the future that a seq_id could be
            #       given to several samples part of a same sequence
            stmt_1 = Query.into("samples_data").insert(
                self.__sample_cnt, self.__sample_cnt, self.__it_cnt, *(fields.get(k, None) for k in fields.keys()))

            # Then add the logs
            # NOTE: For now, the log_id has the same value as the sample_count, but this should be different.
            stmt_2 = Query.into("log_analysis").insert(self.__sample_cnt,
                                                       1 if log_parse_results[0] is True else 0,
                                                       log_parse_results[1],
                                                       log_parse_results[2],
                                                       log_parse_results[3])

            # Execute the two queries
            self.__log.trace("SQL query: {}".format(stmt_1.get_sql(quote_char=None)))
            self.__log.trace("SQL query: {}".format(stmt_2.get_sql(quote_char=None)))
            SqlDb.execute(stmt_1.get_sql(quote_char=None))
            SqlDb.execute(stmt_2.get_sql(quote_char=None))
            SqlDb.commit()
        except Exception as e:
            raise e
        finally:
            SqlDb.disconnect()
    # End def finish_analysis

    # ===== ( Analyze ) ================================================================================================

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

        pkt_fields = dict()
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
            pkt_fields[field['name']] = value

        return pkt_struct, pkt_fields, None
    # End def __read_fuzz_report

    # ==== ( Database Private Methods ) ================================================================================

    def __create_sample_data_table_from_packet_struct(self, pkt_struct):
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
            .create_table("samples_data") \
            .columns(
                Column("sample_id", 'INT', nullable=False),
                Column("seq_id", 'INT', nullable=False),
                Column("iter_id", 'INT', nullable=False),
                *sql_sample_cols) \
            .unique("sample_id", "iter_id") \
            .primary_key("sample_id")

        self.__log.trace("SQL query: {}".format(stmt.get_sql(quote_char=None)))
        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)

            # Clear
            SqlDb.execute('DROP TABLE IF EXISTS `samples_data`')  # Drop the table if it exists
            SqlDb.execute(stmt.get_sql(quote_char=None))  # Create the table
            SqlDb.commit()
            self.__log.debug("SQL database has been cleaned.")
            self.__sample_data_table_created = True

        finally:
            SqlDb.disconnect()
    # End def __create_sample_data_table_from_packet_strut

    def __create_log_analysis_table(self):
        """
        Create the log analysis table
        """
        stmt = Query \
            .create_table("log_analysis") \
            .columns(
                Column("log_id", 'BIGINT', nullable=False),
                Column("has_error", 'BIT', nullable=False),
                Column('error_type', 'VARCHAR(255)', nullable=True),
                Column('error_reason', 'VARCHAR(255)', nullable=True),
                Column('error_effect', 'VARCHAR(255)', nullable=True)) \
            .unique("log_id") \
            .primary_key("log_id")

        try:
            if not SqlDb.is_connected():
                SqlDb.connect(DB_NAME)

            self.__log.info("Clearing the SQL database...")

            # Clear
            SqlDb.execute('DROP TABLE IF EXISTS `log_analysis`')  # Drop the table if it exists
            SqlDb.execute(stmt.get_sql(quote_char=None))  # Create the table
            SqlDb.commit()

            self.__log.debug("SQL database has been cleaned.")
            self.__log_analysis_table_created = True

        finally:
            SqlDb.disconnect()
    # End def __create_log_analysis_table
# End class Analyzer
