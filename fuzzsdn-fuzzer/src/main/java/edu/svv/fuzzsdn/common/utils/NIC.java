package edu.svv.fuzzsdn.common.utils;

import org.pcap4j.core.PcapNativeException;
import org.pcap4j.core.PcapNetworkInterface;
import org.pcap4j.core.Pcaps;

import java.io.IOException;
import java.util.List;

public class NIC
{

    /**
     * Look for NIC interface by its name
     *
     * @param name  Name of the network interface.
     * @return      The pcap network interface corresponding to name.
     * @throws IOException          When there is a PcapNativeException.
     * @throws NullPointerException when there is no NIC to capture from.
     */
    public static PcapNetworkInterface getInterfaceByName(String name) throws IOException, NullPointerException
    {
        List<PcapNetworkInterface> allDevs;
        PcapNetworkInterface networkInterface = null;
        try
        {
            allDevs = Pcaps.findAllDevs();
        }
        catch (PcapNativeException e)
        {
            throw new IOException(e.getMessage());
        }

        // If there are no device to capture from, throw a new exception
        if (allDevs == null || allDevs.isEmpty())
        {
            throw new NullPointerException("No NIF to capture.");
        }

        // Else try to find the NIC
        for (PcapNetworkInterface nic : allDevs)
        {
            if (nic.getName().equals(name))
            {
                networkInterface = nic;
            }
        }

        return networkInterface;
    }
}