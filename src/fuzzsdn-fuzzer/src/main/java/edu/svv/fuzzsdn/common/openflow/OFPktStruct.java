package edu.svv.fuzzsdn.common.openflow;

import edu.svv.fuzzsdn.common.exceptions.NotImplementedException;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import org.jetbrains.annotations.NotNull;
import org.pcap4j.packet.*;
import org.pcap4j.packet.namednumber.EtherType;
import org.pcap4j.packet.namednumber.IpNumber;
import org.projectfloodlight.openflow.protocol.*;
import org.projectfloodlight.openflow.protocol.action.OFAction;
import org.projectfloodlight.openflow.protocol.action.OFActionSetField;
import org.projectfloodlight.openflow.protocol.instruction.OFInstruction;
import org.projectfloodlight.openflow.protocol.instruction.OFInstructionApplyActions;
import org.projectfloodlight.openflow.protocol.instruction.OFInstructionWriteActions;
import org.projectfloodlight.openflow.protocol.oxm.OFOxm;
import org.projectfloodlight.openflow.types.U16;

import java.util.List;

// TODO: Refactor into a PktStruct factory class
public class OFPktStruct
{
    // Get the packet structure from an OFMessage
    @NotNull
    public static PktStruct fromOFMessage(@NotNull OFMessage message)
    {
        PktStruct output = null;

        switch (message.getType())
        {
            case HELLO:
                output = fromOFPTHello((OFHello) message);
                break;

            case BARRIER_REQUEST:
            case BARRIER_REPLY:
                switch (message.getVersion())
                {
                    case OF_13:
                    case OF_14:
                        output = fromBarrierRequestReply0x04();
                        break;
                }
                break;

            case ECHO_REPLY:
            case ECHO_REQUEST:
                output = fromOFPTEcho(message);
                break;

            case ROLE_REQUEST:
                switch (message.getVersion())
                {
                    case OF_13:
                    case OF_14:
                        output = fromRoleRequest0x04();
                        break;
                }
                break;

            case PACKET_IN:
                switch (message.getVersion())
                {
                    case OF_13:
                    case OF_14:
                        output = fromPacketIn0x04((OFPacketIn) message);
                        break;
                }
                break;

            case PACKET_OUT:
                switch (message.getVersion())
                {
                    case OF_13:
                    case OF_14:
                        output = fromPacketOut0x04((OFPacketOut) message);
                        break;
                }
                break;

            case FLOW_MOD:
                output = fromOFPTFlowMod((OFFlowMod) message);
                break;

            case FLOW_REMOVED:
                output = fromOFPTFlowRemoved((OFFlowRemoved) message);
                break;

            default:
                throw new NotImplementedException("Implementation for " + message.getType().toString() + "is not yet supported");
        }

        if (output == null)
            throw new NotImplementedException(
                    "Implementation of OFVersion" +
                            message.getVersion().toString() +
                            " of " +
                            message.getType() +
                            " message is not supported"
            );

        return output;
    }

    // ===== ( OFP Hello Reply ) =======================================================================================

    public static PktStruct fromOFPTHello(@NotNull OFHello msg)
    {
        PktStruct pktStruct = new PktStruct()
                .add(new PktStruct.Field("version"      , 0 , 1))   // header
                .add(new PktStruct.Field("type"         , 1 , 1))   // header
                .add(new PktStruct.Field("length"       , 2 , 2))   // header
                .add(new PktStruct.Field("xid"          , 4 , 4));  // header;

        List<OFHelloElem> elements = msg.getElements();
        int lastOffset = 8;
        if (elements.size() > 0)
        {
            int i = 0;
            for (OFHelloElem element : msg.getElements())
            {
                // Acquire the length of this element
                ByteBuf bb = Unpooled.buffer();
                element.writeTo(bb);
                bb.readerIndex(); // Reset the reader index
                bb.skipBytes(2); // skip the type byte
                int length = U16.f(bb.readShort()); // read the length

                // Add the type and length field
                pktStruct
                        .add(new PktStruct.Field("hello_elem_" + i + "_type" ,  lastOffset , 2))
                        .add(new PktStruct.Field("hello_elem_" + i + "_len"  , lastOffset + 2 , 2));
                lastOffset += 4;

                // Depending on the type, add the elements fields
                if (element.getType() == 1)  // OFPHET_VERSIONBITMAP
                {
                    OFHelloElemVersionbitmap tmp_elem = (OFHelloElemVersionbitmap) element;
                    int bitmap_nb = tmp_elem.getBitmaps().size();

                    for (int j = 0 ; j < bitmap_nb ; j++)
                    {
                        pktStruct.add(new PktStruct.Field("hello_elem_" + i + "_bitmap_" + j, lastOffset, 4));
                        lastOffset += 4;
                    }
                    // NOTE: In the loxigen openflow library, there is no padding in between the elements.
                    //       I'm not sure if it's a bug, or the specification being weird. For now this part is commented
                    //       out
                    // finally add the padding
                    // int pad_length = (length + 7) / 8 * 8 - (length);
                    // if (pad_length > 0)
                    // {
                    //    pktStruct.add(new PktStruct.Field("hello_elem_" + i + "_pad", lastOffset, pad_length));
                    //    lastOffset += pad_length;
                    // }
                }
                else // Default, just add the data as a single field
                {
                    pktStruct.add(new PktStruct.Field("hello_elem_" + i + "_data", 12, length - 4));
                }
                i++;  // increment counter
            }

        }

        return pktStruct;
    }

    // ===== ( OFP Echo Reply ) ========================================================================================


    public static PktStruct fromOFPTEcho(@NotNull OFMessage msg)
    {
        PktStruct pktStruct = new PktStruct()
                .add(new PktStruct.Field("version"      , 0 , 1))   // header
                .add(new PktStruct.Field("type"         , 1 , 1))   // header
                .add(new PktStruct.Field("length"       , 2 , 2))   // header
                .add(new PktStruct.Field("xid"          , 4 , 4));  // header;

        if (msg.getType() == OFType.ECHO_REQUEST)
        {
            OFEchoRequest tmpMsg = (OFEchoRequest) msg;
            pktStruct.add(new PktStruct.Field("data", 5, tmpMsg.getData().length));
        }
        else if (msg.getType() == OFType.ECHO_REPLY)
        {
            OFEchoReply tmpMsg = (OFEchoReply) msg;
            pktStruct.add(new PktStruct.Field("data", 5, tmpMsg.getData().length));
        }
        else
            throw new RuntimeException(
                    "msg being parse is not an Echo Request nor an Echo Reply msg. (got: " +
                    msg.getType().toString() +
                    ")"
            );

        return pktStruct;
    }


    // ===== ( Packet In / Out) ========================================================================================


    public static PktStruct fromPacketIn0x04(@NotNull OFPacketIn msg)
    {
        // Add the first common fields of a PacketIn
        PktStruct pktStruct = new PktStruct()
                .add(new PktStruct.Field("version"  , 0, 1))
                .add(new PktStruct.Field("type"     , 1, 1))
                .add(new PktStruct.Field("length"   , 2, 2))
                .add(new PktStruct.Field("xid"      , 4, 4))
                .add(new PktStruct.Field("buffer_id", 8, 4))
                .add(new PktStruct.Field("total_len", 12, 2))
                .add(new PktStruct.Field("reason"   , 14, 1))
                .add(new PktStruct.Field("table_id" , 15, 1))
                .add(new PktStruct.Field("cookie"   , 16, 8));

        // Parse the match content to know the fields
        pktStruct
                .add(new PktStruct.Field("match_type", 24, 2))
                .add(new PktStruct.Field("match_length", 26, 2));

        int lastOffset = 26;
        int lastLength = 2;

        // Parse each oxm field
        OFOxmList oxmList = ((OFMatchV3) msg.getMatch()).getOxmList();

        int oxm_idx = 0;  // Index used to keep trace of the Oxm Field being parsed
        int oxmStart;

        for (OFOxm<?> oxm : oxmList)
        {
            // Add the common elements of the oxm field
            oxmStart = lastOffset + lastLength;
            pktStruct
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_class", oxmStart, 2))
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_field", oxmStart + 2, 1, true, 0b11111110))
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_has_mask", oxmStart + 2, 1, true, 0b00000001))
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_length", oxmStart + 3, 1));

            // Get the length of the oxm_value field
            int oxmValueLength = (int) oxm.getTypeLen() & 0xFF;
            pktStruct.add(new PktStruct.Field("oxm_" + oxm_idx + "_value", oxmStart + 4, oxmValueLength));

            lastOffset = oxmStart + 4;
            lastLength = oxmValueLength;
            ++oxm_idx;
        }

        // Add the match padding bytes
        ByteBuf bb = Unpooled.buffer();
        msg.getMatch().writeTo(bb);
        bb.readerIndex();
        bb.skipBytes(2);
        int length = U16.f(bb.readShort());
        pktStruct.add(new PktStruct.Field("match_pad", lastOffset + lastLength, (length + 7) / 8 * 8 - length));
        lastOffset = lastOffset + lastLength;
        lastLength = (length + 7) / 8 * 8 - length;

        // Add the padding bytes
        pktStruct.add(new PktStruct.Field("pad", lastOffset + lastLength, 2));
        lastOffset = lastOffset + lastLength;
        lastLength = 2;

        // Add the payload to the packet structure
        // TODO: Factor this part into a single function
        byte[] data = msg.getData();
        try
        {
            EthernetPacket ethPacket = EthernetPacket.newPacket(data, 0, data.length);
            pktStruct.add(fromEthernetPacket(ethPacket));
        }
        catch (IllegalRawDataException | NotImplementedException e)
        {
            // if it's not an ethernet packet then we just add the data as is
            pktStruct.add(new PktStruct.Field("data", lastOffset + lastLength, msg.getData().length));
        }

        return pktStruct;
    }


    public static PktStruct fromPacketOut0x04(OFPacketOut msg)
    {
        // Add the first common fields of a PacketOut
        PktStruct pktStruct = new PktStruct()
                .add(new PktStruct.Field("version"     , 0  , 1))
                .add(new PktStruct.Field("type"        , 1  , 1))
                .add(new PktStruct.Field("length"      , 2  , 2))
                .add(new PktStruct.Field("xid"         , 4  , 4))
                .add(new PktStruct.Field("buffer_id"   , 8  , 4))
                .add(new PktStruct.Field("in_port"     , 12 , 4))
                .add(new PktStruct.Field("actions_len" , 16 , 2))
                .add(new PktStruct.Field("pad"         , 18 , 6));

        // Get the list of actions.
        List<OFAction> actions = msg.getActions();

        int i = 0;
        PktStruct subStruct;
        for (OFAction a : actions)
        {
            subStruct = fromOFAction(a);
            for (int j = 0; j < subStruct.size(); j++)
                subStruct.getByIndex(j).name = "action_" + i + "_"  + subStruct.getByIndex(j).name;
            pktStruct.add(subStruct);
            i++;
        }

        // Add the payload to the packet structure
        // TODO: Factor this part into a single function
        byte[] data = msg.getData();
        try
        {
            EthernetPacket ethPacket = EthernetPacket.newPacket(data, 0, data.length);
            pktStruct.add(fromEthernetPacket(ethPacket));
        }
        catch (IllegalRawDataException | NotImplementedException e)
        {
            // if it's not an ethernet packet then we just add the data as it is
            pktStruct.add(
                    new PktStruct().add(
                            new PktStruct.Field("data", 0, msg.getData().length)
                    )
            );
        }

        return pktStruct;
    }

    // ===== ( OFPT_FLOW_MODE ) ========================================================================================

    public static PktStruct fromOFPTFlowMod(OFFlowMod msg)
    {
        // Add the header fields of a OFPT_FLOW_MOD message
        PktStruct pktStruct = new PktStruct()
                .add(new PktStruct.Field("version"      , 0  , 1))
                .add(new PktStruct.Field("type"         , 1  , 1))
                .add(new PktStruct.Field("length"       , 2  , 2))
                .add(new PktStruct.Field("xid"          , 4  , 4))
                .add(new PktStruct.Field("cookie"       , 8  , 8))
                .add(new PktStruct.Field("cookie_mask"  , 16 , 8))
                .add(new PktStruct.Field("table_id"     , 24 , 1))
                .add(new PktStruct.Field("command"      , 25 , 1))
                .add(new PktStruct.Field("idle_timeout" , 26 , 2))
                .add(new PktStruct.Field("hard_timeout" , 28 , 2))
                .add(new PktStruct.Field("priority"     , 30 , 2))
                .add(new PktStruct.Field("buffer_id"    , 32 , 4))
                .add(new PktStruct.Field("out_port"     , 36 , 4))
                .add(new PktStruct.Field("out_group"    , 40 , 4))
                .add(new PktStruct.Field("flags"        , 44 , 2))
                .add(new PktStruct.Field("importance"   , 46 , 2));

        // Build the match
        pktStruct
                .add(new PktStruct.Field("match_type", 48, 2))
                .add(new PktStruct.Field("match_length", 50, 2));

        // Parse each oxm field
        OFOxmList oxmList = ((OFMatchV3) msg.getMatch()).getOxmList();

        int oxm_idx = 0;  // Index used to keep trace of the Oxm Field being parsed
        int oxmStart;

        for (OFOxm<?> oxm : oxmList)
        {
            // Add the common elements of the oxm field
            oxmStart = pktStruct.last().offset + pktStruct.last().length;
            pktStruct
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_class"    , oxmStart           , 2))
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_field"    , oxmStart + 2 , 1, true, 0b11111110))
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_has_mask" , oxmStart + 2 , 1, true, 0b00000001))
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_length"   , oxmStart + 3 , 1));

            // Get the length of the oxm_value field
            int oxmValueLength = (int) oxm.getTypeLen() & 0xFF;
            pktStruct.add(new PktStruct.Field("oxm_" + oxm_idx + "_value", oxmStart + 4, oxmValueLength));

            ++oxm_idx;
        }

        // Add the match's padding bytes
        ByteBuf bb = Unpooled.buffer();
        msg.getMatch().writeTo(bb);
        bb.readerIndex();
        bb.skipBytes(2);
        int length = U16.f(bb.readShort());
        pktStruct.add(new PktStruct.Field("match_pad", pktStruct.last().offset + pktStruct.last().length, (length + 7) / 8 * 8 - length));


        // Build the instructions fields
        List<OFInstruction> instructionList = msg.getInstructions();
        int instrIdx = 0;
        int instrStart;
        for (OFInstruction instruction : instructionList)
        {
            instrStart = pktStruct.last().offset + pktStruct.last().length;
            pktStruct
                    .add(new PktStruct.Field("instr_" + instrIdx + "_type" , instrStart     , 2))
                    .add(new PktStruct.Field("instr_" + instrIdx + "_len"  , instrStart + 2 , 2));

            // Update the instrStart after lastOffset and last Length
            instrStart = pktStruct.last().offset + pktStruct.last().length;
            switch (instruction.getType())
            {
                case GOTO_TABLE:
                    pktStruct
                            .add(new PktStruct.Field("instr_" + instrIdx + "_table_id" , instrStart     , 1))
                            .add(new PktStruct.Field("instr_" + instrIdx + "_pad"      , instrStart + 1 , 3));
                    break;

                case WRITE_METADATA:
                    pktStruct
                            .add(new PktStruct.Field("instr_" + instrIdx + "_pad"           , instrStart     , 4))
                            .add(new PktStruct.Field("instr_" + instrIdx + "_metadata"      , instrStart + 4 , 8))
                            .add(new PktStruct.Field("instr_" + instrIdx + "_metadata_mask" , instrStart + 12 , 8));
                    break;

                case WRITE_ACTIONS:
                case APPLY_ACTIONS:
                case CLEAR_ACTIONS:
                    pktStruct.add(new PktStruct.Field("instr_" + instrIdx + "_pad", instrStart, 4));

                    // Get the action list
                    List<OFAction> actionList = null;
                    if (instruction.getType() == OFInstructionType.WRITE_ACTIONS)
                        actionList = ((OFInstructionWriteActions) instruction).getActions();
                    else if (instruction.getType() == OFInstructionType.APPLY_ACTIONS)
                        actionList = ((OFInstructionApplyActions) instruction).getActions();

                    if (actionList != null)
                    {
                        PktStruct subStruct;
                        int actionIdx = 0;
                        for (OFAction action : actionList)
                        {
                            subStruct = fromOFAction(action);
                            for (int j = 0 ; j < subStruct.size() ; j++)
                                subStruct.getByIndex(j).name = "instr_" + instrIdx + "_action_" + actionIdx + "_" + subStruct.getByIndex(j).name;
                            pktStruct.add(subStruct);
                            actionIdx++;
                        }
                    }
                    break;

                case METER:
                    pktStruct.add(new PktStruct.Field("instr_" + instrIdx + "_meter_id", instrStart, 4));
                    break;

                case EXPERIMENTER:
                    pktStruct.add(new PktStruct.Field("instr_" + instrIdx + "_experimenter", instrStart, 4));
                    // NB: There seem to be no support in the openflow library for experimenter data.
                    break;
            }

            instrIdx++; // increment the instruction idx
        }

        return pktStruct;

    }

    // ===== ( OFPT_FLOW_MODE ) ========================================================================================

    public static PktStruct fromOFPTFlowRemoved(OFFlowRemoved msg)
    {
        // Add the header fields of a OFPT_FLOW_MOD message
        PktStruct pktStruct = new PktStruct()
                .add(new PktStruct.Field("version"       , 0  , 1))
                .add(new PktStruct.Field("type"          , 1  , 1))
                .add(new PktStruct.Field("length"        , 2  , 2))
                .add(new PktStruct.Field("xid"           , 4  , 4))
                .add(new PktStruct.Field("cookie"        , 8  , 8))
                .add(new PktStruct.Field("priority"      , 16 , 2))
                .add(new PktStruct.Field("reason"        , 18 , 1))
                .add(new PktStruct.Field("table_id"      , 19 , 1))
                .add(new PktStruct.Field("duration_sec"  , 20 , 4))
                .add(new PktStruct.Field("duration_nsec" , 24 , 4))
                .add(new PktStruct.Field("idle_timeout"  , 28 , 2))
                .add(new PktStruct.Field("hard_timeout"  , 30 , 2))
                .add(new PktStruct.Field("packet_count"  , 32 , 8))
                .add(new PktStruct.Field("byte_count"    , 40 , 8));

        // Build the match
        pktStruct
                .add(new PktStruct.Field("match_type", 48, 2))
                .add(new PktStruct.Field("match_length", 50, 2));

        // Parse each oxm field
        OFOxmList oxmList = ((OFMatchV3) msg.getMatch()).getOxmList();

        int oxm_idx = 0;  // Index used to keep trace of the Oxm Field being parsed
        int oxmStart;

        for (OFOxm<?> oxm : oxmList)
        {
            // Add the common elements of the oxm field
            oxmStart = pktStruct.last().offset + pktStruct.last().length;
            pktStruct
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_class"    , oxmStart           , 2))
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_field"    , oxmStart + 2 , 1, true, 0b11111110))
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_has_mask" , oxmStart + 2 , 1, true, 0b00000001))
                    .add(new PktStruct.Field("oxm_" + oxm_idx + "_length"   , oxmStart + 3 , 1));

            // Get the length of the oxm_value field
            int oxmValueLength = (int) oxm.getTypeLen() & 0xFF;
            pktStruct.add(new PktStruct.Field("oxm_" + oxm_idx + "_value", oxmStart + 4, oxmValueLength));

            ++oxm_idx;
        }

        // Add the match's padding bytes
        ByteBuf bb = Unpooled.buffer();
        msg.getMatch().writeTo(bb);
        bb.readerIndex();
        bb.skipBytes(2);
        int length = U16.f(bb.readShort());
        pktStruct.add(new PktStruct.Field("match_pad", pktStruct.last().offset + pktStruct.last().length, (length + 7) / 8 * 8 - length));

        return pktStruct;

    }

    // ===== ( OFP Barrier Request / Reply ) ===========================================================================


    public static PktStruct fromBarrierRequestReply0x04()
    {
        return new PktStruct()
                .add(new PktStruct.Field("version"      , 0 , 1))   // header
                .add(new PktStruct.Field("type"         , 1 , 1))   // header
                .add(new PktStruct.Field("length"       , 2 , 2))   // header
                .add(new PktStruct.Field("xid"          , 4 , 4));   // header;
    }

    // ===== ( OFP Role Request ) ===============================================================================

    // OFPT_ROLE_REQUEST structure is unchanged between ofp 1.3 and 1.4
    public static PktStruct fromRoleRequest0x04()
    {
        return new PktStruct()
                .add(new PktStruct.Field("version"      , 0 , 1))   // header
                .add(new PktStruct.Field("type"         , 1 , 1))   // header
                .add(new PktStruct.Field("length"       , 2 , 2))   // header
                .add(new PktStruct.Field("xid"          , 4 , 4))   // header
                .add(new PktStruct.Field("role"         , 8 , 4))   // role
                .add(new PktStruct.Field("pad"          , 12, 4))   // pad
                .add(new PktStruct.Field("generation_id", 16, 8));
    }

    // ===== ( Internet Protocols ) ====================================================================================

    public static PktStruct fromOFAction(@NotNull OFAction action)
    {
        // Get the common action and type, etc.
        OFVersion version = action.getVersion();
        OFActionType actionType = action.getType();

        // Add the header
        PktStruct pktStruct = new PktStruct()
                .add(new PktStruct.Field("type", 0, 2))
                .add(new PktStruct.Field("len", 2, 2));

        switch  (actionType)
        {
            // ofp_action_output
            case OUTPUT:
                pktStruct
                        .add(new PktStruct.Field("port",4,4))
                        .add(new PktStruct.Field("max_len", 8,2))
                        .add(new PktStruct.Field("pad",10,6));
                break;

            // ofp_action_generic
            case COPY_TTL_OUT:
            case COPY_TTL_IN:
            case DEC_MPLS_TTL:
            case DEC_NW_TTL:
            case POP_VLAN:
            case POP_PBB:
                pktStruct.add(new PktStruct.Field("pad",4,4));
                break;

            // ofp_action_mpls_ttl
            case SET_MPLS_TTL:
                pktStruct
                        .add(new PktStruct.Field("mpls_ttl",4,1))
                        .add(new PktStruct.Field("pad",5,3));
                break;

            // ofp_action_push, ofp_action_pop_mpls, ofp_action_push_pbb
            case PUSH_VLAN:
            case POP_MPLS:
            case PUSH_PBB:
                pktStruct
                        .add(new PktStruct.Field("ethertype",4,2))
                        .add(new PktStruct.Field("pad",6,2));
                break;

            // ofp_action_set_queue
            case SET_QUEUE:
                pktStruct.add(new PktStruct.Field("queue_id",4,4));
                break;

            // ofp_action_group
            case GROUP:
                pktStruct.add(new PktStruct.Field("group_id",4,4));
                break;

            // ofp_action_nw_ttl
            case SET_NW_TTL:
                pktStruct
                        .add(new PktStruct.Field("new_ttl",4,1))
                        .add(new PktStruct.Field("pad",5,3));
                break;

            // ofp_action_set_field
            case SET_FIELD:
                // Get the OXM
                OFActionSetField field_act = (OFActionSetField) action;
                ByteBuf bb = Unpooled.buffer();
                field_act.getField().writeTo(bb);
                int oxmLen = bb.readableBytes();
                pktStruct.add(new PktStruct.Field("oxm",4,oxmLen));
                pktStruct.add(new PktStruct.Field("pad", 4+oxmLen, ((oxmLen + 4) + 7)/8*8 - (oxmLen + 4)));
                break;

            // ofp_action_experimenter_header
            case EXPERIMENTER:
                pktStruct.add(new PktStruct.Field("experimenter",4,4));
                break;

            default:
                throw new NotImplementedException(
                        "Handling of OFAction not implement for OpenFlow version " +
                        version.toString()
                );
        }

        return pktStruct;
    }
    // ===== ( Internet Protocols ) ====================================================================================

    @NotNull
    public static PktStruct fromEthernetPacket(@NotNull EthernetPacket ethPacket)
    {
        PktStruct pktStruct = new PktStruct(
                new PktStruct.Field("eth_src", 0, 6),
                new PktStruct.Field("eth_dst", 6, 6),
                new PktStruct.Field("ethertype", 12, 2)
        );

        EtherType payloadType = ethPacket.getHeader().getType();
        PktStruct payloadPacket;
        boolean foundEthPacket = true;
        switch ((int) payloadType.value())
        {
            case 0x0806:  // ARP
                payloadPacket = fromARPPacket((ArpPacket) ethPacket.getPayload());
                break;

            case 0x0800:  // IPv4
                payloadPacket = fromIPV4Packet((IpV4Packet) ethPacket.getPayload());
                break;

            case 0x86DD: // IPv6
                payloadPacket = fromIPV6Packet((IpV6Packet) ethPacket.getPayload());
                break;

            default:
                payloadPacket = new PktStruct(
                        new PktStruct.Field("eth_data", 14, ethPacket.getPayload().getRawData().length)
                );
                foundEthPacket = false;
        }

        pktStruct.add(payloadPacket);
        // Add the padding byte
        if (foundEthPacket)
        {
            if (ethPacket.getPad().length > 0)
            {
                pktStruct.add(
                        new PktStruct.Field(
                                "eth_pad",
                                14 + payloadPacket.byteLength(),
                                ethPacket.getPad().length
                        )
                );
            }
        }

        return pktStruct;
    }

    @NotNull
    public static PktStruct fromARPPacket(@NotNull ArpPacket arpPacket)
    {
        PktStruct pktStruct = new PktStruct(
                new PktStruct.Field("arp_htype", 0, 2),
                new PktStruct.Field("arp_ptype", 2, 2),
                new PktStruct.Field( "arp_hlen", 4, 1),
                new PktStruct.Field( "arp_plen", 5, 1),
                new PktStruct.Field ("arp_oper", 6, 2)
        );

        ArpPacket.ArpHeader header = arpPacket.getHeader();
        int hwAddrLength = header.getHardwareAddrLengthAsInt();
        int prtAddrLength = header.getProtocolAddrLengthAsInt();

        pktStruct
                .add(new PktStruct.Field( "arp_sha"  ,  8, hwAddrLength))
                .add(new PktStruct.Field( "arp_spa"  ,  8 + hwAddrLength, prtAddrLength))
                .add(new PktStruct.Field( "arp_tha"  ,  8 + hwAddrLength + prtAddrLength, hwAddrLength))
                .add(new PktStruct.Field( "arp_tpa"  ,  8 + 2*hwAddrLength + prtAddrLength, prtAddrLength));


        return pktStruct;
    }

    public static PktStruct fromIPV4Packet(IpV4Packet ipv4Packet)
    {
        PktStruct pktStruct = new PktStruct(
                new PktStruct.Field("ipv4_version"        , 0  , 1  , true , 0xF0)   ,
                new PktStruct.Field("ipv4_ihl"            , 0  , 1  , true , 0x0F)   ,
                new PktStruct.Field("ipv4_tos"            , 1  , 1) ,
                new PktStruct.Field("ipv4_total_len"      , 2  , 2) ,
                new PktStruct.Field("ipv4_identification" , 4  , 2) ,
                new PktStruct.Field("ipv4_flags"          , 6  , 2  , true , 0xE000) ,
                new PktStruct.Field("ipv4_frag_off"       , 6  , 2  , true , 0x1FFF) ,
                new PktStruct.Field("ipv4_ttl"            , 8  , 1) ,
                new PktStruct.Field("ipv4_protocol"       , 9  , 1) ,
                new PktStruct.Field("ipv4_checksum"       , 10 , 2) ,
                new PktStruct.Field("ipv4_src_addr"       , 12 , 4) ,
                new PktStruct.Field("ipv4_dst_addr"       , 16 , 4)
        );

        IpV4Packet.IpV4Header header = ipv4Packet.getHeader();

        // compute the options if there are some
        if (header.getIhlAsInt() > 5)
        {
            int i = 0;
            for (IpV4Packet.IpV4Option o : header.getOptions())
            {
                PktStruct optionStruct = new PktStruct()
                        .add(new PktStruct.Field("ipv4_opt_" + i + "_copied", 0, 1, true, 0x40))
                        .add(new PktStruct.Field("ipv4_opt_" + i + "_class" , 0, 1, true, 0x20))
                        .add(new PktStruct.Field("ipv4_opt_" + i + "_num"   , 0, 1, true, 0x1F));

                if (o.length() > 1)
                {
                    optionStruct.add("ipv4_opt_" + i + "_len" , 1             , false, 0);
                    optionStruct.add("ipv4_opt_" + i + "_data", o.length() - 2, false, 0);
                }

                // Append the options to the pktstruct
                pktStruct.add(optionStruct, true);

                // Increase option length
                i++;
            }

        }

        IpNumber payloadType = header.getProtocol();

        PktStruct payloadPacket;
        try
        {
            // TODO: Parse the inner packets
            switch ((int) payloadType.value())
            {
                case 0x01: // ICMP
                case 0x02: // IGMP
                case 0x06: // TCP
                case 0x11: // UDP
                case 0x29: // ENCAP
                case 0x59: // OSPF
                case 0x84: // SCTP
                default:
                    payloadPacket = new PktStruct(
                            new PktStruct.Field("ipv4_data", 0, ipv4Packet.getPayload().getRawData().length)
                    );
            }
        }
        catch (NullPointerException e)
        {
            payloadPacket = null;
        }

        if (payloadPacket != null)
            pktStruct.add(payloadPacket, true);

        return pktStruct;
    }


    public static PktStruct fromIPV6Packet(IpV6Packet ipv6Packet)
    {
        throw new NotImplementedException("IPV6 packet decoding not yet implemented");

    }

}