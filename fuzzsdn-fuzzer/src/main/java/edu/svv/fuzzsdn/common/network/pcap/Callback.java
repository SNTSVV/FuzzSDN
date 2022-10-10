package edu.svv.fuzzsdn.common.network.pcap;

import org.pcap4j.packet.Packet;

/**
 * An Object that can receive and handle a pcap4j packet.
 */
public interface Callback
{
    /**
     * The methods that is called by the pcap4j handle.
     *
     * @param packet the pcap4j packet to handle
     */
    void packetReceivedCallback(Packet packet);
}
