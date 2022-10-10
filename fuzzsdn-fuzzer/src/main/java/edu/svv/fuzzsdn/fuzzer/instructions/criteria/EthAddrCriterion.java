package edu.svv.fuzzsdn.fuzzer.instructions.criteria;


import org.pcap4j.packet.EthernetPacket;
import org.pcap4j.packet.IllegalRawDataException;
import org.pcap4j.util.MacAddress;
import org.projectfloodlight.openflow.protocol.OFMessage;
import org.projectfloodlight.openflow.protocol.OFPacketIn;
import org.projectfloodlight.openflow.protocol.OFPacketOut;
import org.projectfloodlight.openflow.protocol.OFType;

public class EthAddrCriterion extends Criterion<MacAddress>
{
    private final boolean matchSourceAddress;

    // ===== ( Constructor ) ===========================================================================================

    public EthAddrCriterion(boolean srcAddr, MacAddress... values)
    {
        super(MacAddress.class, values);
        this.matchSourceAddress = srcAddr;
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * See {@link Criterion#isSatisfied}
     */
    @Override
    public boolean isSatisfied(OFMessage msg)
    {
        if (msg.getType() == OFType.PACKET_IN || msg.getType() == OFType.PACKET_OUT)
        {
            EthernetPacket ethPacket;
            try
            {
                if (msg.getType() == OFType.PACKET_IN)
                {
                    OFPacketIn packetIn = (OFPacketIn) msg;
                    ethPacket = EthernetPacket.newPacket(packetIn.getData(), 0, packetIn.getData().length);
                }
                else
                {
                    OFPacketOut packetOut = (OFPacketOut) msg;
                    ethPacket = EthernetPacket.newPacket(packetOut.getData(), 0, packetOut.getData().length);
                }
            }
            catch (IllegalRawDataException e) // A malformed Ethernet packet (or not one)
            {
                return false;
            }

            // Return true if the src or dst header is included
            if (matchSourceAddress)
                return (values.contains(ethPacket.getHeader().getSrcAddr()));
            else
                return (values.contains(ethPacket.getHeader().getDstAddr()));

        }
        else
            return false;
    }

}

