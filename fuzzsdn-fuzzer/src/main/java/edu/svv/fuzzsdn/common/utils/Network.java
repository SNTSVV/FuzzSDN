package edu.svv.fuzzsdn.common.utils;

import org.pcap4j.core.NotOpenException;
import org.pcap4j.core.PcapHandle;
import org.pcap4j.core.PcapNativeException;
import org.pcap4j.packet.ArpPacket;
import org.pcap4j.packet.EthernetPacket;
import org.pcap4j.packet.Packet;
import org.pcap4j.packet.namednumber.ArpHardwareType;
import org.pcap4j.packet.namednumber.ArpOperation;
import org.pcap4j.packet.namednumber.EtherType;
import org.pcap4j.util.ByteArrays;
import org.pcap4j.util.MacAddress;

import java.io.IOException;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.concurrent.ThreadLocalRandom;

public class Network
{

    public static MacAddress getLocalMacFromIP(InetAddress IP) throws IOException
    {
        NetworkInterface device = null;

        // Wait to find the device thanks to the IP address
        while(device == null)
        {
            device = NetworkInterface.getByInetAddress(IP);
        }

        // Return the Mac Address as a MacAddress Object
        byte[] mac = device.getHardwareAddress();
        return MacAddress.getByAddress(mac);
    }

    /**
     * Generate a random MAC address
     *
     * @return A string containing the random MAC address
     */
    public static String getRandomMACAddress()
    {
        byte[] macAddr = new byte[6];
        StringBuilder sb = new StringBuilder(18);
        ThreadLocalRandom.current().nextBytes(macAddr);

        for(byte b : macAddr)
        {
            if(sb.length() > 0)
                sb.append(":");
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }


    /**
     *  Identifies the Mac Address of a device with a given IP
     *
     * @param handle PcapHandle used to find get the MAC address
     * @param localIP IP of the current network device
     * @param localMac MAC of the current network device
     * @param IP IP of the device to detect the mac from
     * @return Detected MacAddress object
     * @throws PcapNativeException
     * @throws NotOpenException
     */
    public static MacAddress getMac(PcapHandle handle,
                                    InetAddress localIP,
                                    MacAddress localMac,
                                    InetAddress IP) throws PcapNativeException, NotOpenException
    {
        Packet request_packet = buildArpPacket(ArpOperation.REQUEST,
                                               localIP, localMac,
                                               IP, MacAddress.ETHER_BROADCAST_ADDRESS);
        handle.sendPacket(request_packet);

        while(true)
        {
            Packet packet = handle.getNextPacket();
            if (packet == null)
            {
                continue;
            }

            ArpPacket arp = packet.get(ArpPacket.class);
            if(arp.getHeader().getSrcProtocolAddr().equals(IP) &&
               arp.getHeader().getOperation().equals(ArpOperation.REPLY))
            {
                return arp.getHeader().getSrcHardwareAddr();
            }
        }
    }

    /**
     * Builds an ARP packet
     *
     * @param type ARP operation (REPLY, REQUEST)
     * @param srcIP IP of the source device
     * @param srcMAC MAC of the source device
     * @param dstIP IP of the destination device
     * @param dstMAC MAC of the destination device
     */
    public static Packet buildArpPacket(ArpOperation type,
                                        InetAddress  srcIP,
                                        MacAddress   srcMAC,
                                        InetAddress  dstIP,
                                        MacAddress   dstMAC)
    {

        // Build the ARP Payload
        ArpPacket.Builder arpBuilder = new ArpPacket.Builder();
        arpBuilder
                .hardwareType(ArpHardwareType.ETHERNET)
                .protocolType(EtherType.IPV4)
                .hardwareAddrLength((byte) MacAddress.SIZE_IN_BYTES)
                .protocolAddrLength((byte) ByteArrays.INET4_ADDRESS_SIZE_IN_BYTES)
                .operation(type)
                .srcHardwareAddr(srcMAC)
                .srcProtocolAddr(srcIP)
                .dstHardwareAddr(dstMAC)
                .dstProtocolAddr(dstIP);

        // Build the encapsulating Ethernet packet
        EthernetPacket.Builder etherBuilder = new EthernetPacket.Builder();
        etherBuilder
                .dstAddr(dstMAC)
                .srcAddr(srcMAC)
                .type(EtherType.ARP)
                .payloadBuilder(arpBuilder)
                .paddingAtBuild(true);

        // Return the build ethernet packet
        return etherBuilder.build();
    }

}
