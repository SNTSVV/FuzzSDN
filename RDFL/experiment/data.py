#!/usr/bin/env python3
# coding: utf-8

# Introduction

"""
The purpose of this code is to generate the on
"""
import binascii
import csv

from utils.database import Database as SqlDb
from utils.terminal import progress_bar

## Settings
PRINT_STATISTICS = False  # default=True
KEEP_TRACE_ON_UNKNOWN = False  # default=True
SQL_DB_ADDRESS = "10.240.5.104"
SQL_DB_USER = "dev"
SQL_DB_PASSWORD = "b14724x"

# ---------
# Main code
# ---------

BYTES_CSV_COLUMNS = {
    "data"          : 0,
    "error_type"    : 1,
    "error_reason"  : 2,
    "error_effect"  : 3,
    "error_trace"   : 4
}

# Dictionary used to produce statistics about the quantity of errors
STATS = {
    "total": 0,
    "total_logs": 0,
    "errors": []
}


def parse_errors(error_list, row, error_index, reason_index, effect_index, trace_index):
    error = None
    reason = None
    effect = None

    for error_line in error_list:
        # First try to find errors
        if error is None:
            # Parsing Errors
            if "org.projectfloodlight.openflow.exceptions.OFParseError" in error_line[1]:
                error = "parsing_error"

                # Illegal PacketIn
                if "Illegal wire value for type OFPacketInReason" in error_line[1]:
                    reason = "illegal_packet_in_reason"

                # Illegal Match
                elif "Wrong type: Expected=0x1(0x1)" in error_line[1]:
                    reason = "illegal_match_type"

                elif "Unknown value for discriminator typeLen of class OFOxmVer14" in error_line[1]:
                    reason = "illegal_match_typelen"

                # Unknown error
                else:
                    reason = error_line[1]
                continue  # Skip the reason detection

            # Buffer Under Flow errors
            if "java.nio.BufferUnderflowException" in error_line[1]:
                error = "buffer_underflow"

            # Null Pointer Exceptions
            if "java.lang.NullPointerException" in error_line[1]:
                error = "null_pointer_exception"

            # Bad Action Error Msg
            if "OFBadActionErrorMsgVer14" in error_line[1]:
                error = "bad_action"
                if "code=BAD_OUT_PORT" in error_line[1]:
                    reason = "bad_out_port"
                continue

            if "org.onlab.packet.DeserializationException" in error_line[1]:
                error = "packet_deserialization_exception"

        # Handle Reason
        if reason is None:
            if "OFPacketInVer14: property match cannot be null" in error_line[1]:
                reason = "null_packet_in_property_match"

            # Issue while decoding the ethernet packet
            if "Packet deserialization problem" in error_line[1]:
                reason = "ethernet_deserialization_problem"

        # Handle effects
        if "*** Onos has crashed ***" in error_line[1]:
            effect = "onos_controller_crash"

        if "*** Mininet has crashed ***" in error_line[1]:
            effect = "mininet_crash"

        if effect is None:
            # Switch Disconnection
            if "Switch disconnected callback" in error_line[1]:
                effect = "switch_disconnected"

    # If we couldn't find an error, say that the error is unknown
    if error is None:
        error = "Unknown"

    # If we couldn't find an reason, say that the reason is unknown
    if reason is None:
        reason = "Unknown"

    if effect is None:
        effect = "Unknown"

    # Finally, add the error, reason, effect and trace to the row
    row[error_index] = error
    row[reason_index] = reason
    row[effect_index] = effect

    STATS["errors"] += [(error, reason, effect)]

    # If one of the error, reason or effect is unknown, keep the trace
    if KEEP_TRACE_ON_UNKNOWN and (error == "Unknown" or reason == "Unknown" or effect == "Unknown"):
        row[trace_index] = "\n".join(["{}: {}".format(entry[0], entry[1]) for entry in error_list])
# End def parse_errors


# End def decode_data_field

def fetch(csv_path: str):
    """
    Fetch the data from the experiment database
    :param csv_path:
    :return:
    """
    # Initialize database
    if not SqlDb.is_init:
        SqlDb.init(SQL_DB_ADDRESS, SQL_DB_USER, SQL_DB_PASSWORD)

    with open(csv_path, "w") as csv_file:

        csv_writer  = csv.writer(csv_file, delimiter=";")

        if KEEP_TRACE_ON_UNKNOWN is True:
            csv_writer.writerow(list(BYTES_CSV_COLUMNS.keys()))
        else:
            csv_writer.writerow(list(BYTES_CSV_COLUMNS.keys())[:-1])

        # Get the count of data
        conn1, cursor1 = SqlDb.get_connection("control_flow_fuzzer")
        conn2, cursor2 = SqlDb.get_connection("control_flow_fuzzer")

        try:

            cursor1.execute("SELECT COUNT(*) FROM fuzzed_of_message")
            STATS["total"] = cursor1.fetchone()[0]
            msg_count = 0
            # fetch rows one by one to limit memory usage
            print("Fetching {} fuzzed messages...".format(STATS["total"]))
            cursor1.execute("SELECT * FROM fuzzed_of_message ORDER BY date")
            current_message = cursor1.fetchone()
            next_message = cursor1.fetchone()

            cursor2.execute("SELECT COUNT(*) FROM log_error")
            STATS["total_logs"] = cursor2.fetchone()[0]
            print("Fetching {} log entries...".format(STATS["total_logs"]))
            cursor2.execute("SELECT * FROM log_error ORDER BY date DESC")
            log_entry = list(cursor2.fetchall())

            print("Assembling data...")
            progress_bar(0, STATS["total"], prefix='Progress:', suffix='Complete', length=100)
            while next_message is not None:

                current_date = current_message[1]
                next_date = next_message[1]
                log_match = []

                # # Complexity: O((n^2 - n))
                # for j in range(len(errors) - 1, -1, -1):
                #     if current_date <= errors[j][1] < next_date:
                #         error += errors[j][3] + "|"
                #         del errors[j]  # Delete errors handled as we proceed

                # Complexity: O(sqrt(n))
                for j in range(len(log_entry) - 1, -1, -1):
                    if current_date <= log_entry[j][1] < next_date:
                        if log_entry[j][3] is not None:
                            # Store a tuple of the level and the error message
                            log_match += [(log_entry[j][2], log_entry[j][3])]
                        # Delete errors handled as we proceed
                        del log_entry[j]

                    if log_entry[j][1] > next_date:
                        # since the dates are sorted by descending order, we can safely break out of the loop if we
                        # go over the next_date
                        break

                ############
                # handle data as byte
                byte_csv_row = [None] * len(BYTES_CSV_COLUMNS) if KEEP_TRACE_ON_UNKNOWN else [None] * (len(BYTES_CSV_COLUMNS) - 1)
                byte_csv_row[BYTES_CSV_COLUMNS["data"]] = binascii.b2a_base64(current_message[3], newline=False).decode()  # Store the data
                parse_errors(log_match, byte_csv_row,
                             error_index=BYTES_CSV_COLUMNS["error_type"],
                             reason_index=BYTES_CSV_COLUMNS["error_reason"],
                             effect_index=BYTES_CSV_COLUMNS["error_effect"],
                             trace_index=BYTES_CSV_COLUMNS["error_trace"])

                # Writing data of CSV file
                csv_writer.writerow(byte_csv_row)

                # finally, set the next message as the current message
                current_message = next_message
                next_message = cursor1.fetchone()

                # Update progress bar
                msg_count += 1
                progress_bar(msg_count,
                             STATS["total"] - 1,
                             prefix='Progress:',
                             suffix='Complete',
                             length=100)

        finally:
            # Close the cursors and the connections to avoid any issues
            cursor1.close()
            cursor2.close()
            conn1.close()
            conn2.close()
    # End with

    if PRINT_STATISTICS is True:
        print("###############\n"
              "# STATISTICS: #\n"
              "###############\n")

        error_stats = STATS["errors"]
        nb_fm = STATS.pop("total")
        nb_log = STATS.pop("total_logs")
        print("Number of entries:", nb_fm)
        print("Repartition of errors:")

        rep_dict = dict()
        for stat in error_stats:
            if stat[0] in rep_dict:
                rep_dict[stat[0]] += 1
            else:
                rep_dict[stat[0]] = 1

        for key in rep_dict:
            print("\t- {}: {} ({:.3f}%)".format(key, rep_dict[key], float(rep_dict[key]) / float(nb_fm) * 100.0))

        print("Repartition of reason:")
        rep_dict = dict()
        for stat in error_stats:
            if stat[0] not in rep_dict:
                rep_dict[stat[0]] = dict()

            if stat[1] not in rep_dict[stat[0]]:
                rep_dict[stat[0]][stat[1]] = 1
            else:
                rep_dict[stat[0]][stat[1]] += 1

        for key in rep_dict:
            print("\t- {}:".format(key))
            for key2 in rep_dict[key]:
                print("\t\t- {}: {} ({:.3f}%)".format(key2, rep_dict[key][key2],
                                                      float(rep_dict[key][key2]) / float(nb_fm) * 100.0))


# -----
# Leftover
# ------