package edu.svv.fuzzsdn.common.network;

import edu.svv.fuzzsdn.common.utils.Network;
import org.pcap4j.core.*;
import org.pcap4j.core.PcapNetworkInterface.PromiscuousMode;
import org.pcap4j.packet.namednumber.ArpOperation;
import org.pcap4j.util.MacAddress;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Implement a Spoofer that use ARP packets to redirect messages between two IP addresses
 */
public class ARPSpoofer
{

    // Static variables
    private static final int MIN_PERIOD = 250; // ms

    // Logger
    private final Logger log;

    // Switch IP and Mac
    private InetAddress srcAIP;
    private MacAddress  srcAMAC;
    private InetAddress srcBIP;
    private MacAddress  srcBMAC;
    private int         mPeriod;  // Period at which the ARP spoof message should be sent

    // Network Interface
    private PcapNetworkInterface mDevice;
    private PcapHandle mHandle;

    // Spoof Service Scheduler
    private final ScheduledExecutorService mSpoofService = Executors.newScheduledThreadPool(1);

    // ===== (Constructor) =============================================================================================

    public ARPSpoofer()
    {
        this(null);
    }

    public ARPSpoofer(PcapNetworkInterface device)
    {
        this.mDevice = device;

        // Setup the logger
        this.log = LoggerFactory.getLogger(String.format("%s-%d", ARPSpoofer.class.getName(), this.hashCode()));
    }

    // ===== (Getters) =================================================================================================

    public boolean isSpoofing()
    {
        return !mSpoofService.isShutdown();
    }
    // ===== (Setters) =================================================================================================

    /**
     * Set the IP address of the first source to be spoofed
     *
     * @param IPAddress The IP address of the source to be spoofed
     * @throws UnknownHostException when the IP's source cannot be found
     */
    public void setSourceA(String IPAddress) throws UnknownHostException
    {
         this.srcAIP = InetAddress.getByName(IPAddress);
         this.srcAMAC = null;  // Reset the mac address to enable new calculation
    }

    /**
     * Set the IP address of the first source to be spoofed
     *
     * @param IPAddress The IP address of the source to be spoofed
     * @throws UnknownHostException when the IP's source cannot be found
     */
    public void setSourceB(String IPAddress) throws UnknownHostException
    {
        this.srcBIP = InetAddress.getByName(IPAddress);
        this.srcBMAC = null; // Reset the mac address to enable new calculation
    }

    public void setPeriod(int period)
    {
        // No less than MIN_PERIOD milliseconds
        this.mPeriod = Math.max(period, MIN_PERIOD);
    }


    public void setNetworkDevice(PcapNetworkInterface device)
    {
        this.mDevice = device;
    }


    // ===== (Public Methods) ==========================================================================================

    /**
     * Starts the Spoofer
     */
    public void start()
    {
        if (mDevice == null)
        {
            log.warn("No device selected");
            return;
        }

        // Close and reset the handle
        if (mHandle != null)
            if (mHandle.isOpen())
                mHandle.close();

        this.mHandle = null;  // Reset the handle

        try
        {
            // Create a new network handle
            mHandle = new PcapHandle.Builder(mDevice.getName())
                    .snaplen(65535)            // 2^16
                    .promiscuousMode(PromiscuousMode.PROMISCUOUS)
                    .timeoutMillis(100)        // ms
                    .bufferSize(1024 * 1024)   // 1 MB
                    .build();

            // Filter the handle so we only get ARP messages
            String filter = "arp";
            mHandle.setFilter(filter, BpfProgram.BpfCompileMode.OPTIMIZE);

            // Get the Mac Address and IP of the local network interface
            InetAddress localIP = mDevice.getAddresses().get(0).getAddress();
            MacAddress localMac = Network.getLocalMacFromIP(localIP);

            System.out.println("Device IP: " + localIP.getHostAddress());
            System.out.println("Device MAC: " + localMac.toString());

            // Get the MAC address of source A and B
            srcAMAC = Network.getMac(mHandle, localIP, localMac, srcAIP);
            srcBMAC = Network.getMac(mHandle, localIP, localMac, srcBIP);

            System.out.println("A IP: " + srcAIP.getHostAddress());
            System.out.println("A MAC: " + srcAMAC.toString());

            System.out.println("B IP: " + srcBIP.getHostAddress());
            System.out.println("B MAC: " + srcBMAC.toString());

            // Schedule a task that sends ARP packets with given interval
            mSpoofService.scheduleAtFixedRate(() -> {
                try
                {
                    // Send an ARP packet so that A -> [channel] -> B
                    mHandle.sendPacket(Network.buildArpPacket(ArpOperation.REPLY, srcAIP, localMac, srcBIP, srcBMAC));
                    // Send an ARP packet so that B -> [channel] -> A
                    mHandle.sendPacket(Network.buildArpPacket(ArpOperation.REPLY, srcBIP, localMac, srcAIP, srcAMAC));
                }
                catch (NotOpenException e)
                {
                    log.error("Network handle is closed. ARP messages cannot be sent.");
                }
                catch (PcapNativeException e)
                {
                    log.error("Caught PcapNativeException while sending ARP messages", e);
                }
            }, 0, mPeriod, TimeUnit.MILLISECONDS);
        }
        catch (PcapNativeException | NotOpenException | IOException e)
        {
            e.printStackTrace();
        }
    }

    /**
     * Stops the Spoofer
     */
    public void stop() throws InterruptedException
    {
        if (!mSpoofService.isShutdown())
        {
            log.debug("Stopping the executor.");
            mSpoofService.shutdown();
            if (!mSpoofService.awaitTermination(2000, TimeUnit.MILLISECONDS))
            {
                System.out.println("Couldn't stop spoofer");
            }
            else
            {
                System.out.println("Spoofer stopped");
            }

            // Un-spoof the targets
            log.info("Resetting the network.");

            try
            {
                // Send an ARP packet so that A -> B
                mHandle.sendPacket(Network.buildArpPacket(ArpOperation.REPLY, srcAIP, srcAMAC, srcBIP, srcBMAC));
                // Send an ARP packet so that B -> A
                mHandle.sendPacket(Network.buildArpPacket(ArpOperation.REPLY, srcBIP, srcBMAC, srcAIP, srcAMAC));

            }
            catch (NotOpenException e)
            {
                log.error("Network handle is already closed. Cannot reset the network", e);
            }
            catch (PcapNativeException e)
            {
                log.error("Caught PcapNativeException while resetting the network", e);
            }
        }

    }

}
