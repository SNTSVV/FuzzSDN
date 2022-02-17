#!/usr/bin/env python3
# coding: utf-8
"""Defines of enum for errors on openflow v1.4 (0x05)."""

from enum import IntEnum


class ErrorType(IntEnum):
    """
    Values for ’type’ in ofp_error_message.

    These values are immutable: they will not change in future versions of the protocol (although new values may be
    added).
    """

    OFPET_HELLO_FAILED            = 0       # Hello Failed
    OFPET_BAD_REQUEST             = 1       # Bad Request
    OFPET_BAD_ACTION              = 2       # Bad Action
    OFPET_BAD_INSTRUCTION         = 3       # Bad Instruction
    OFPET_BAD_MATCH               = 4       # Bad Match
    OFPET_FLOW_MOD_FAILED         = 5       # Flow Mod Failed
    OFPET_GROUP_MOD_FAILED        = 6       # Group Mod Failed
    OFPET_PORT_MOD_FAILED         = 7       # Port Mod Failed
    OFPET_TABLE_MOD_FAILED        = 8       # Table Mod Failed
    OFPET_QUEUE_OP_FAILED         = 9       # Queue Op Failed'
    OFPET_SWITCH_CONFIG_FAILED    = 10      # Switch Config Failed
    OFPET_ROLE_REQUEST_FAILED     = 11      # Role Request Failed
    EXPERIMENTER                  = 0xFFFF  # Experimenter

    @property
    def code_class(self):
        """Return a Code class based on current ErrorType value.
        Returns:
            enum.IntEnum: class referenced by current error type.
        """
        classes = {
            'OFPET_HELLO_FAILED'              : HelloFailedCode,
            'OFPET_BAD_REQUEST'               : BadRequestCode,
            'OFPET_BAD_ACTION'                : BadActionCode,
            'OFPET_BAD_INSTRUCTION'           : BadInstructionCode,
            'OFPET_BAD_MATCH'                 : BadMatchCode,
            'OFPET_FLOW_MOD_FAILED'           : FlowModFailedCode,
            'OFPET_GROUP_MOD_FAILED'          : GroupModFailedCode,
            'OFPET_PORT_MOD_FAILED'           : PortModFailedCode,
            'OFPET_QUEUE_OP_FAILED'           : QueueOpFailedCode,
            'OFPET_SWITCH_CONFIG_FAILED'      : SwitchConfigFailedCode,
            'OFPET_ROLE_REQUEST_FAILED'       : RoleRequestFailedCode,
            'OFPET_TABLE_MOD_FAILED'          : TableModFailedCode
        }
        return classes.get(self.name, GenericFailedCode)
# End class ErrorType


class GenericFailedCode(IntEnum):
    """
    Error_msg 'code' values for OFPET_BAD_ACTION.
    'data' contains at least the first 64 bytes of the failed request.
    """
    GENERIC_ERROR = 0  # Unknown error
# End class GenericFailedCode


class HelloFailedCode(IntEnum):
    OFPHFC_INCOMPATIBLE = 0  # No compatible version.
    OFPHFC_EPERM        = 1  # Permissions error.
# End class HelloFailedCode


class BadRequestCode(IntEnum):
    OFPBRC_BAD_VERSION                  = 0  # ofp_header.version not supported.
    OFPBRC_BAD_TYPE                     = 1  # ofp_header.type not supported.
    OFPBRC_BAD_MULTIPART                = 2  # ofp_multipart_request.type not supported.
    OFPBRC_BAD_EXPERIMENTER             = 3  # Experimenter id not supported (in ofp_experimenter_header or ofp_multipart_request or ofp_multipart_reply).
    OFPBRC_BAD_EXP_TYPE                 = 4  # Experimenter type not supported.
    OFPBRC_EPERM                        = 5  # Permissions error.
    OFPBRC_BAD_LEN                      = 6  # Wrong request length for type.
    OFPBRC_BUFFER_EMPTY                 = 7  # Specified buffer has already been used.
    OFPBRC_BUFFER_UNKNOWN               = 8  # Specified buffer does not exist.
    OFPBRC_BAD_TABLE_ID                 = 9  # Specified table-id invalid or does not exist.
    OFPBRC_IS_SLAVE                     = 10  # Denied because controller is slave.
    OFPBRC_BAD_PORT                     = 11  # Invalid port.
    OFPBRC_BAD_PACKET                   = 12  # Invalid packet in packet-out
    OFPBRC_MULTIPART_BUFFER_OVERFLOW    = 13  # ofp_multipart_request iverflowed the assigned buffer.
    OFPBRC_MULTIPART_REQUEST_TIMEOUT    = 14  # Timeout during multipart request.
    OFPBRC_MULTIPART_REPLY_TIMEOUT      = 15  # Timeout during multipart reply.
# End class BadRequestCode


class BadActionCode(IntEnum):
    OFPBAC_BAD_TYPE             = 0  # Unknown action type.
    OFPBAC_BAD_LEN              = 1  # Length problem in actions.
    OFPBAC_BAD_EXPERIMENTER     = 2  # Unknown experimenter id specified.
    OFPBAC_BAD_EXP_TYPE         = 3  # Unknown action type for experimenter id.
    OFPBAC_BAD_OUT_PORT         = 4  # Problem validating output action.
    OFPBAC_BAD_ARGUMENT         = 5  # Bad action argument.
    OFPBAC_EPERM                = 6  # Permissions error.
    OFPBAC_TOO_MANY             = 7  # Can't handle this many actions.
    OFPBAC_BAD_QUEUE            = 8  # Problem validating output queue.
    OFPBAC_BAD_OUT_GROUP        = 9  # Invalid group id in forward action.
    OFPBAC_MATCH_INCONSISTENT   = 10  # Action can't apply for this match, or Set-Field missing prerequisite.
    OFPBAC_UNSUPPORTED_ORDER    = 11  # Action order is unsupported for the action list in an Apply-Actions instruction
    OFPBAC_BAD_TAG              = 12  # Actions uses an unsupported tag/encap.
    OFPBAC_BAD_SET_TYPE         = 13  # Unsupported type in SET_FIELD action.
    OFPBAC_BAD_SET_LEN          = 14  # Length problem in SET_FIELD action.
    OFPBAC_BAD_SET_ARGUMENT     = 15  # Bad arguement in SET_FIELD action.
# End class BadActionCode


class BadInstructionCode(IntEnum):
    OFPBIC_UNKNOWN_INST         = 0  # Unknown instruction.
    OFPBIC_UNSUP_INST           = 1  # Switch or table does not support  the instruction.
    OFPBIC_BAD_TABLE_ID         = 2  # Invalid Table-Id specified
    OFPBIC_UNSUP_METADATA       = 3  # Metadata value unsupported by datapath.
    OFPBIC_UNSUP_METADATA_MASK  = 4  # Metadata mask value unsupported by datapath.
    OFPBIC_BAD_EXPERIMENTER     = 5  # Unknown experimenter id specified.
    OFPBIC_BAD_EXP_TYPE         = 6  # Unknown instruction for experimenter id.
    OFPBIC_BAD_LEN              = 7  # Length problem in instrucitons.
    OFPBIC_EPERM                = 8  # Permissions error.
    OFPBIC_DUP_INST             = 9  # Duplicate instruction.
# End class BadInstructionCode


class BadMatchCode(IntEnum):
    OFPBMC_BAD_TYPE         = 0  # Unsupported match type specified by the match.
    OFPBMC_BAD_LEN          = 1  # Length problem in math.
    OFPBMC_BAD_TAG          = 2  # Match uses an unsupported tag/encap.
    OFPBMC_BAD_DL_ADDR_MASK = 3  # Unsupported datalink addr mask - switch does not support arbitrary datalink address mask.
    OFPBMC_BAD_NW_ADDR_MASK = 4  # Unsupported network addr mask - switch does not support arbitrary network addres mask.
    OFPBMC_BAD_WILDCARDS    = 5  # Unsupported combination of fields masked or omitted in the match.
    OFPBMC_BAD_FIELD        = 6  # Unsupported field type in the match.
    OFPBMC_BAD_VALUE        = 7  # Unsupported value in a match field.
    OFPBMC_BAD_MASK         = 8  # Unsupported mask specified in the match.
    OFPBMC_BAD_PREREQ       = 9  # A prerequisite was not met.
    OFPBMC_DUP_FIELD        = 10  # A field type was duplicated.
    OFPBMC_EPERM            = 11  # Permissions error.
# End class BadMatchCode


class FlowModFailedCode(IntEnum):
    OFPFMFC_UNKNOWN         = 0  # Unspecified error.
    OFPFMFC_TABLE_FULL      = 1  # Flow not added because table was full.
    OFPFMFC_BAD_TABLE_ID    = 2  # Table does not exist
    OFPFMFC_OVERLAP         = 3  # Attempted to add overlapping flow with CHECK_OVERLAP flag set.
    OFPFMFC_EPERM           = 4  # Permissions error.
    OFPFMFC_BAD_TIMEOUT     = 5  # Flow not added because of unsupported idle/hard timeout.
    OFPFMFC_BAD_COMMAND     = 6  # Unsupported or unknown command.
    OFPFMFC_BAD_FLAGS       = 7  # Unsupported or unknown flags.
    OFPFMFC_CANT_SYNC       = 8  # Problem in table synchronisation.
    OFPFMFC_BAD_PRIORITY    = 9  # Unsupported priority value.
# End class FlowModFailedCode


class GroupModFailedCode(IntEnum):
    OFPGMFC_GROUP_EXISTS            = 0  # Group not added because a group ADD attempted to replace an already-present group.
    OFPGMFC_INVALID_GROUP           = 1  # Group not added because Group specified is invalid.
    OFPGMFC_WEIGHT_UNSUPPORTED      = 2  # Switch does not support unequal load sharing with select groups.
    OFPGMFC_OUT_OF_GROUPS           = 3  # The group table is full.
    OFPGMFC_OUT_OF_BUCKETS          = 4  # The maximum number of action buckets for a group has been exceeded.
    OFPGMFC_CHAINING_UNSUPPORTED    = 5  # Switch does not support groups that forward to groups.
    OFPGMFC_WATCH_UNSUPPORTED       = 6  # This group cannot watch the watch_port or watch_group specified.
    OFPGMFC_LOOP                    = 7  # Group entry would cause a loop.
    OFPGMFC_UNKNOWN_GROUP           = 8  # Group not modified because a group MODIFY attempted to modify a non-existent group.
    OFPGMFC_CHAINED_GROUP           = 9  # Group not deleted because another group is forwarding to it.
    OFPGMFC_BAD_TYPE                = 10  # Unsupported or unknown group type.
    OFPGMFC_BAD_COMMAND             = 11  # Unsupported or unknown command.
    OFPGMFC_BAD_BUCKET              = 12  # Error in bucket.
    OFPGMFC_BAD_WATCH               = 13  # Error in watch port/group.
    OFPGMFC_EPERM                   = 14  # Permissions error.
# End class GroupModFailedCode


class PortModFailedCode(IntEnum):
    OFPPMFC_BAD_PORT        = 0  # Specified port does not exist.
    OFPPMFC_BAD_HW_ADDR     = 1  # Specified hardware address does not match the port number.
    OFPPMFC_BAD_CONFIG      = 2  # Specified config is invalid.
    OFPPMFC_BAD_ADVERTISE   = 3  # Specified advertise is invalid.
    OFPPMFC_EPERM           = 4  # Permissions error.
# End class PortModFailedCode


class TableModFailedCode(IntEnum):
    OFPTMFC_BAD_TABLE   = 0  # Specified table does not exist.
    OFPTMFC_BAD_CONFIG  = 1  # Specified config is invalid.
    OFPTMFC_EPERM       = 2  # Permissions error
# End class TableModFailedCode


class QueueOpFailedCode(IntEnum):
    OFPQOFC_BAD_PORT    = 0  # Invalid port (or port does not exist).
    OFPQOFC_BAD_QUEUE   = 1  # Queue does not exist.
    OFPQOFC_EPERM       = 2  # Permissions error.
# End class QueueOpFailedCode


class SwitchConfigFailedCode(IntEnum):
    OFPSCFC_BAD_FLAGS   = 0  # Specified flags is invalid.
    OFPSCFC_BAD_LEN     = 1  # Specified len is invalid.
    OFPSCFC_EPERM       = 2  # Permissions error.
# End class SwitchConfigFailedCode


class RoleRequestFailedCode(IntEnum):
    OFPRRFC_STALE       = 0  # Stale Message: old generation_id.
    OFPRRFC_UNSUP       = 1  # Controller role change unsupported.
    OFPRRFC_BAD_ROLE    = 2  # Invalid role.
# End class RoleRequestFailedCode
