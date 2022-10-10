package edu.svv.fuzzsdn.common.openflow;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.ByteBufUtil;
import io.netty.buffer.Unpooled;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.pcap4j.packet.*;
import org.pcap4j.packet.namednumber.*;
import org.pcap4j.util.MacAddress;
import org.projectfloodlight.openflow.protocol.*;
import org.projectfloodlight.openflow.protocol.action.OFAction;
import org.projectfloodlight.openflow.protocol.match.MatchField;
import org.projectfloodlight.openflow.protocol.oxm.OFOxmBsnIngressPortGroupId;
import org.projectfloodlight.openflow.protocol.ver13.OFFactoryVer13;
import org.projectfloodlight.openflow.protocol.ver14.OFActionsVer14;
import org.projectfloodlight.openflow.protocol.ver14.OFFactoryVer14;
import org.projectfloodlight.openflow.protocol.ver14.OFOxmsVer14;
import org.projectfloodlight.openflow.types.*;

import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Set;

// TODO: Generate random packet in and test randomly several of them
class OFPktStructTest
{

    private static final SecureRandom random = new SecureRandom();

    // ===== (from OFPT_HELLO tests) ====

    @Test
    void fromOFPHello_checkLength_Equals()
    {
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFHello.Builder builder = factory.buildHello();
        OFHelloElemVersionbitmap.Builder EVMBuilder1 = factory.buildHelloElemVersionbitmap();
        OFHelloElemVersionbitmap.Builder EVMBuilder2 = factory.buildHelloElemVersionbitmap();
        List<U32> bitmap1 = Arrays.asList(U32.of(0x00000012), U32.of(0x00010032));
        List<U32> bitmap2 = Arrays.asList(U32.of(0x0000000F), U32.of(0x00010032));

        // Build the elements
        List<OFHelloElem> elements = new ArrayList<>();
        elements.add(EVMBuilder1.setBitmaps(bitmap1).build());
        elements.add(EVMBuilder2.setBitmaps(bitmap2).build());

        builder
                .setXid(0x12345678)
                .setElements(elements);

        OFHello helloBuilt = builder.build();

        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromOFPTHello(helloBuilt);

        // Write to a buffer
        ByteBuf bb = Unpooled.buffer();
        helloBuilt.writeTo(bb);
        int actualLength = bb.readableBytes();

        Assertions.assertEquals(actualLength, pktStruct.byteLength());
    }

    // ===== (from OFPT_ECHO tests) ====

    @Test
    void fromOFPEcho_checkLength_Equals_whenTypeIsEchoRequest()
    {
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFEchoRequest.Builder builder = factory.buildEchoRequest();
        builder
                .setXid(0x12345678)
                .setData(new byte[] {0x00, 0x01, 0x02, 0x3, (byte) 0xFF, (byte) 0x0A});

        OFEchoRequest ofEchoRequest = builder.build();

        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromOFPTEcho(ofEchoRequest);

        // Write to a buffer
        ByteBuf bb = Unpooled.buffer();
        ofEchoRequest.writeTo(bb);
        int actualLength = bb.readableBytes();

        Assertions.assertEquals(actualLength, pktStruct.byteLength());

    }

    @Test
    void fromOFPEcho_checkLength_Equals_whenTypeIsEchoReply()
    {
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFEchoReply.Builder builder = factory.buildEchoReply();
        builder
                .setXid(0x12345678)
                .setData(new byte[] {0x00, 0x01, 0x02, 0x3, (byte) 0xFF, (byte) 0x0A});

        OFEchoReply ofEchoReply = builder.build();

        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromOFPTEcho(ofEchoReply);

        // Write to a buffer
        ByteBuf bb = Unpooled.buffer();
        ofEchoReply.writeTo(bb);
        int actualLength = bb.readableBytes();

        Assertions.assertEquals(actualLength, pktStruct.byteLength());

    }

    // ===== (from PacketIn tests) ====
    @Test
    void fromPacketIn0x04_checkLength_Equals()
    {
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFPacketIn.Builder builder = factory.buildPacketIn();

        builder
                .setXid(0x12345678)
                .setBufferId(OFBufferId.of(100))
                .setTotalLen(17000)
                .setReason(OFPacketInReason.ACTION)
                .setTableId(TableId.of(20))
                .setCookie(U64.parseHex("FEDCBA9876543210"))
                .setMatch(
                        factory.buildMatchV3()
                                .setMasked(MatchField.IN_PORT, OFPort.of(4), OFPort.of(5))
                                .setExact(MatchField.ARP_OP, ArpOpcode.REQUEST)
                                .setExact(MatchField.IPV4_DST, IPv4Address.of(50005))
                                .build()
                )
                .setData(new byte[] { 97, 98, 99 } );
        OFPacketIn packetInBuilt = builder.build();

        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromPacketIn0x04(packetInBuilt);


        ByteBuf bb = Unpooled.buffer();
        packetInBuilt.writeTo(bb);
        int actualLength = bb.readableBytes();

        Assertions.assertEquals(actualLength, pktStruct.byteLength());
    }

    @Test
    void fromPacketIn0x04_checkLengthWithARPMessage_Equals()
    {
        OFFactory factory = OFFactoryVer13.INSTANCE;
        OFPacketIn.Builder packetInBuilder = factory.buildPacketIn();

        packetInBuilder
                .setXid(0x12345678)
                .setBufferId(OFBufferId.of(100))
                .setTotalLen(17000)
                .setReason(OFPacketInReason.ACTION)
                .setTableId(TableId.of(20))
                .setCookie(U64.parseHex("FEDCBA9876543210"))
                .setMatch(
                        factory.buildMatchV3()
                                .setExact(MatchField.ARP_OP, ArpOpcode.REQUEST)
                                .build()
                );

        // Build the arp message
        EthernetPacket ethPacket = null;
        try
        {
            EthernetPacket.Builder ethBuilder = new EthernetPacket.Builder()
                    .paddingAtBuild(true)
                    .type(EtherType.ARP)
                    .srcAddr(MacAddress.getByName("00:00:00:00:00:01"))
                    .dstAddr(MacAddress.getByName("00:00:00:00:00:02"))
                    .payloadBuilder(new ArpPacket.Builder()
                            .operation(ArpOperation.REQUEST)
                            .hardwareType(ArpHardwareType.ETHERNET)
                            .protocolType(EtherType.IPV4)
                            .srcHardwareAddr(MacAddress.getByName("00:00:00:00:00:01"))
                            .dstHardwareAddr(MacAddress.getByName("00:00:00:00:00:02"))
                            .srcProtocolAddr(Inet4Address.getByName("10.0.0.1"))
                            .dstProtocolAddr(Inet4Address.getByName("10.0.0.2"))
                            .hardwareAddrLength((byte) 6)
                            .protocolAddrLength((byte) 4)
                    );

            ethPacket = ethBuilder.build();
        }
        catch (UnknownHostException ignored) { }

        if (ethPacket == null) throw new AssertionError();
        packetInBuilder.setData(ethPacket.getRawData());
        OFPacketIn packetInBuilt = packetInBuilder.build();

        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromPacketIn0x04(packetInBuilt);

        ByteBuf bb = Unpooled.buffer();
        packetInBuilt.writeTo(bb);
        int actualLength = bb.readableBytes();

        Assertions.assertEquals(actualLength, pktStruct.byteLength());
    }

    // ===== (from PacketOut tests) ====

    @Test
    void fromPacketOut0x04_checkLength_Equals()
    {
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFPacketOut.Builder builder = factory.buildPacketOut();
        // Prepare the actions
        List<OFAction> actions = new java.util.ArrayList<>();
        actions.add(OFActionsVer14.INSTANCE.output(OFPort.ANY, 15));
        actions.add(OFActionsVer14.INSTANCE.copyTtlOut());
        actions.add(OFActionsVer14.INSTANCE.copyTtlIn());
        // Build the packet
        builder
                .setXid(0x12345678)
                .setBufferId(OFBufferId.of(100))
                .setInPort(OFPort.ofShort((short) 123))
                .setActions(actions)
                .setData(new byte[] { 97, 98, 99 } );

        OFPacketOut packetOutBuilt = builder.build();
        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromPacketOut0x04(packetOutBuilt);
        // Check the length is correct
        ByteBuf bb = Unpooled.buffer();
        packetOutBuilt.writeTo(bb);
        Assertions.assertEquals(bb.readableBytes(), pktStruct.byteLength());
    }

    // ===== (from BarrierRequest tests) ====

    @Test
    void fromBarrierRequest_checkLength_Equals()
    {
        // Build the OFP_BARRIER_REQUEST message
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFBarrierRequest.Builder barrierRequestBuilder = factory.buildBarrierRequest();
        barrierRequestBuilder.setXid(0x0123456789FEDCBAL);
        OFBarrierRequest barrierRequestMessage = barrierRequestBuilder.build();

        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromOFMessage(barrierRequestMessage);

        // Compare it to the actual length of the message
        ByteBuf bb = Unpooled.buffer();
        barrierRequestMessage.writeTo(bb);
        int actualLength = bb.readableBytes();

        Assertions.assertEquals(actualLength, pktStruct.byteLength());
    }

    // ===== (from RoleRequest tests) ====

    @Test
    void fromRoleRequest_checkLength_Equals()
    {
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFRoleRequest.Builder roleRequestBuilder = factory.buildRoleRequest();

        roleRequestBuilder
                .setXid(0x012345678ABCDEFL)
                .setRole(OFControllerRole.ROLE_SLAVE)
                .setGenerationId(U64.parseHex("fabcde123456789"));

        OFRoleRequest roleRequestMessage = roleRequestBuilder.build();

        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromOFMessage(roleRequestMessage);

        ByteBuf bb = Unpooled.buffer();
        roleRequestMessage.writeTo(bb);
        int actualLength = bb.readableBytes();

        Assertions.assertEquals(actualLength, pktStruct.byteLength());
    }

    // ===== (from OFPT_FLOW_MODE tests) =====

    @Test
    void fromFlowMod_checkLength_Equals()
    {
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFFlowMod.Builder flowModifyBuilder = factory.buildFlowModify();

        flowModifyBuilder
                .setCookie(U64.of(3500))
                .setCookieMask(U64.of(0x111))
                .setXid(0x012345678ABCDEFL)
                .setBufferId(OFBufferId.of(50))
                .setFlags(Set.of(
                        OFFlowModFlags.BSN_SEND_IDLE,
                        OFFlowModFlags.CHECK_OVERLAP)
                )
                .setOutPort(OFPort.of(0))
                .setOutGroup(OFGroup.ANY)
                .setPriority(1)
                .setImportance(500)
                .setHardTimeout(10000)
                .setIdleTimeout(1000)
                .setMatch(
                        factory.buildMatchV3()
                                .setMasked(MatchField.BSN_IFP_CLASS_ID, ClassId.of(50), ClassId.FULL_MASK)
                                .setExact(MatchField.IN_PORT, OFPort.of(0xFEFEFE))
                                .build()
                )
                .setInstructions(
                        List.of(
                                factory.instructions().buildApplyActions()
                                        .setActions(
                                                List.of(
                                                        factory.actions().buildOutput().setMaxLen(500).setPort(OFPort.of(6)).build(),
                                                        factory.actions().buildOutput().setMaxLen(500).setPort(OFPort.of(6)).build()
                                                )
                                        ).build(),
                                factory.instructions().buildApplyActions()
                                        .setActions(
                                                List.of(
                                                        factory.actions().buildGroup().setGroup(OFGroup.of(999999999)).build()
                                                )
                                        ).build()
                        )
                );


        OFFlowMod flowModMessage = flowModifyBuilder.build();

        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromOFPTFlowMod(flowModMessage);

        ByteBuf bb = Unpooled.buffer();
        flowModMessage.writeTo(bb);
        int actualLength = bb.readableBytes();

        System.out.println(flowModMessage);
        System.out.println(ByteBufUtil.prettyHexDump(bb));
        for (int i=0 ; i< pktStruct.size(); i++)
            System.out.println(pktStruct.getByIndex(i));

        Assertions.assertEquals(actualLength, pktStruct.byteLength());
    }

    // ===== (from OFPT_FLOW_REMOVED tests) =====

    @Test
    void fromFlowRemoved_checkLength_Equals()
    {
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFFlowRemoved.Builder flowRemovedBuilder = factory.buildFlowRemoved();

        flowRemovedBuilder
                .setXid(0x012345678ABCDEFL)
                .setCookie(U64.of(3500))
                .setPriority(1)
                .setReason(OFFlowRemovedReason.EVICTION)
                .setTableId(TableId.of(6))
                .setHardTimeout(10000)
                .setIdleTimeout(1000)
                .setPacketCount(U64.of(6753423L))
                .setByteCount(U64.of(99999999999L))
                .setMatch(
                        factory.buildMatchV3()
                                .setMasked(MatchField.BSN_IFP_CLASS_ID, ClassId.of(50), ClassId.FULL_MASK)
                                .setExact(MatchField.IN_PORT, OFPort.of(0xFEFEFE))
                                .build()
                );

        OFFlowRemoved flowRemovedMessage = flowRemovedBuilder.build();
        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromOFPTFlowRemoved(flowRemovedMessage);

        ByteBuf bb = Unpooled.buffer();
        flowRemovedMessage.writeTo(bb);
        int actualLength = bb.readableBytes();

        System.out.println(flowRemovedMessage);
        System.out.println(ByteBufUtil.prettyHexDump(bb));
        for (int i=0 ; i< pktStruct.size(); i++)
            System.out.println(pktStruct.getByIndex(i));

        Assertions.assertEquals(actualLength, pktStruct.byteLength());
    }

    // ===== (from OFAction tests) ====

    @Test
    void fromOFAction_checkLength_Equals()
    {
        for (OFActionType ofpat : OFActionType.values())
        {
            OFAction action = null;
            PktStruct struct;

            switch  (ofpat)
            {
                // ofp_action_output
                case OUTPUT:
                    action = OFActionsVer14.INSTANCE.output(OFPort.ALL, 50);

                    break;

                // ofp_action_generic
                case COPY_TTL_OUT:
                    action = OFActionsVer14.INSTANCE.copyTtlOut();
                    break;

                case COPY_TTL_IN:
                    action = OFActionsVer14.INSTANCE.copyTtlIn();
                    break;

                case DEC_MPLS_TTL:
                    action = OFActionsVer14.INSTANCE.decMplsTtl();
                    break;

                case DEC_NW_TTL:
                    action = OFActionsVer14.INSTANCE.decNwTtl();
                    break;

                case POP_VLAN:
                    action = OFActionsVer14.INSTANCE.popVlan();
                    break;

                case POP_PBB:
                    action = OFActionsVer14.INSTANCE.popPbb();
                    break;

                // ofp_action_mpls_ttl
                case SET_MPLS_TTL:
                    action = OFActionsVer14.INSTANCE.setMplsTtl((short) 1);
                    break;

                // ofp_action_push, ofp_action_pop_mpls, ofp_action_push_pbb
                case PUSH_VLAN:
                    action = OFActionsVer14.INSTANCE.pushVlan(EthType.ARP);
                    break;

                case POP_MPLS:
                    action = OFActionsVer14.INSTANCE.popMpls(EthType.ARP);
                    break;

                case PUSH_PBB:
                    action = OFActionsVer14.INSTANCE.pushPbb(EthType.ARP);
                    break;

                // ofp_action_set_queue
                case SET_QUEUE:
                    action = OFActionsVer14.INSTANCE.setQueue(123456789);
                    break;

                // ofp_action_group
                case GROUP:
                    action = OFActionsVer14.INSTANCE.group(OFGroup.ANY);
                    break;

                // ofp_action_nw_ttl
                case SET_NW_TTL:
                    action = OFActionsVer14.INSTANCE.setNwTtl((short) 123);
                    break;

                // ofp_action_set_field
                case SET_FIELD:
                    OFOxmBsnIngressPortGroupId oxm = OFOxmsVer14.INSTANCE.bsnIngressPortGroupId(ClassId.of(556));
                    action = OFActionsVer14.INSTANCE.setField(oxm);
                    break;

                // ofp_action_experimenter_header
                case EXPERIMENTER:
                    // skipped for now
                    break;
            }

            if (action != null)
            {
                // Get the structure
                struct = OFPktStruct.fromOFAction(action);
                // Write the action to a byte buffer
                ByteBuf bb = Unpooled.buffer();
                action.writeTo(bb);
                // Perform the check on the length of the structure
                String msgIfFailed = "action=" + action.toString();
                Assertions.assertEquals(bb.readableBytes(), struct.byteLength(), msgIfFailed);
                System.out.println(bb.readableBytes());
                System.out.println(struct);
            }
        }



        OFFactory factory = OFFactoryVer13.INSTANCE;
        OFPacketIn.Builder builder = factory.buildPacketIn();

        builder
                .setXid(0x12345678)
                .setBufferId(OFBufferId.of(100))
                .setTotalLen(17000)
                .setReason(OFPacketInReason.ACTION)
                .setTableId(TableId.of(20))
                .setCookie(U64.parseHex("FEDCBA9876543210"))
                .setMatch(
                        factory.buildMatchV3()
                                .setMasked(MatchField.IN_PORT, OFPort.of(4), OFPort.of(5))
                                .setExact(MatchField.ARP_OP, ArpOpcode.REQUEST)
                                .setExact(MatchField.IPV4_DST, IPv4Address.of(50005))
                                .build()
                )
                .setData(new byte[] { 97, 98, 99 } );
        OFPacketIn packetInBuilt = builder.build();

        // Build the packet structure from the OF message
        PktStruct pktStruct = OFPktStruct.fromOFMessage(packetInBuilt);


        ByteBuf bb = Unpooled.buffer();
        packetInBuilt.writeTo(bb);
        int actualLength = bb.readableBytes();

        Assertions.assertEquals(actualLength, pktStruct.byteLength());
    }


    // ===== ( Internet Packet ) ====
    @Test
    void fromIpv4Packet_checkLength_Equals_withNoOptions() throws UnknownHostException
    {
        IpV4Packet packet = new IpV4Packet.Builder()
                .version(IpVersion.IPV4)
                .protocol(IpNumber.IPV4)
                .tos(IpV4Rfc1349Tos.newInstance((byte)0))
                .ttl((byte) 23)
                .srcAddr((Inet4Address)InetAddress.getByName("17.48.35.191"))
                .dstAddr((Inet4Address)InetAddress.getByName("138.210.237.120"))
                .correctChecksumAtBuild(true)
                .correctLengthAtBuild(true)
                .payloadBuilder(
                        new UnknownPacket.Builder()
                                .rawData(new byte[]{1, 2, 3, 4, 5})
                )
                .build();

        PktStruct pktStruct = OFPktStruct.fromIPV4Packet(packet);

        Assertions.assertEquals(packet.length(), pktStruct.byteLength());

    }

    @Test
    void fromIpv4Packet_checkLength_Equals_withOptions() throws UnknownHostException
    {
        List<IpV4Packet.IpV4Option> options = new ArrayList<>();
        options.add(IpV4NoOperationOption.getInstance());
        options.add(IpV4NoOperationOption.getInstance());
        options.add(IpV4NoOperationOption.getInstance());
        options.add(IpV4EndOfOptionList.getInstance());


        IpV4Packet packet = new IpV4Packet.Builder()
                .version(IpVersion.IPV4)
                .protocol(IpNumber.IPV4)
                .tos(IpV4Rfc1349Tos.newInstance((byte)0))
                .ttl((byte) 23)
                .srcAddr((Inet4Address)InetAddress.getByName("17.48.35.191"))
                .dstAddr((Inet4Address)InetAddress.getByName("138.210.237.120"))
                .options(options)
                .correctChecksumAtBuild(true)
                .correctLengthAtBuild(true)
                .payloadBuilder(
                        new UnknownPacket.Builder()
                                .rawData(new byte[]{1, 2, 3, 4, 5})
                )
                .build();

        PktStruct pktStruct = OFPktStruct.fromIPV4Packet(packet);

        Assertions.assertEquals(packet.length(), pktStruct.byteLength());

    }

}