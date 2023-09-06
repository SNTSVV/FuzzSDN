package edu.svv.fuzzsdn.fuzzer;

import edu.svv.fuzzsdn.common.network.pcap.Listener;
import edu.svv.fuzzsdn.common.network.tcpproxy.TCPProxy;
import edu.svv.fuzzsdn.common.utils.NIC;
import edu.svv.fuzzsdn.common.utils.Utils;
import edu.svv.fuzzsdn.fuzzer.configuration.AppPaths;
import edu.svv.fuzzsdn.fuzzer.configuration.Configuration;
import org.apache.commons.lang3.time.StopWatch;
import org.pcap4j.core.NotOpenException;
import org.pcap4j.core.PcapNativeException;
import org.pcap4j.core.PcapNetworkInterface;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;


// TODO add Javadocs once Core class is finished

public class Core
{
    // ===== ( Parameters ) ============================================================================================

    // Logger
    private static final Logger log = LoggerFactory.getLogger(Core.class);

    // Singleton instance
    private static Core instance = null;

    private final TCPProxy mProxy;
    private final Listener mListener;
    private final Fuzzer mPacketFuzzer;

    // Thread Executor
    private final ExecutorService mThreadPool = Executors.newFixedThreadPool(10);

    // Configuration
    public static int EXIT_TIMEOUT = 6000; // ms
    private final Configuration mConfig;


    // ===== ( Constructor and getInstance) ============================================================================

    private Core()
    {
        log.info("Setting up {}", getClass().getSimpleName());

        this.mConfig        = Configuration.getInstance();
        this.mListener      = new Listener();

        // Set up the fuzzer
        this.mPacketFuzzer  = new Fuzzer();

        // Set up the proxy
        this.mProxy         = new TCPProxy();

    }

    // ===== ( Public Method ) =========================================================================================

    /**
     * Return a singleton instance of the Core class. If the function is called for the first time,
     * initialize the singleton instance.
     *
     * @return the singleton instance of the Core class
     */
    public static Core getInstance()
    {
        if (instance == null)
            synchronized (Core.class) { instance = new Core(); }
        return instance;
    }

    /**
     * Starts the core
     */
    public void start()
    {
        log.info("Starting {}", getClass().getSimpleName());

        // 1. Start the Packet Listener if a packet trace is enabled
        if (mConfig.getBoolean("KeepPacketTrace"))
        {
            log.info("Configuring Packet Listener...");
            if (!Utils.isNullOrEmpty(mConfig.get("NIC")))
            {
                try
                {
                    PcapNetworkInterface device = NIC.getInterfaceByName(mConfig.get("NIC"));
                    if (device != null)
                    {
                        String fileName = LocalDateTime.now() + "-" + Configuration.PID + ".pcap";
                        mListener
                                .setNetworkDevice(device)
                                .setMaxPackets(-1)
                                .setDumpFile(
                                        AppPaths.userCacheDir()
                                                .resolve("pcaps")
                                                .resolve(fileName)
                                                .toString()
                                )
                                .setFilter(mConfig.get("PcapFilter"))
                                .enableDump(true)
                                .setup();

                        // Add listener to the packet queue
                        log.info("Starting Packet Listener.");
                        mThreadPool.execute(mListener);
                    }
                    else
                    {
                        log.error("Device " + mConfig.get("NIC") + " doesn't exist. Disabling packet capture.");
                    }
                }
                catch (NullPointerException e)
                {
                    // There is no NIC so we disable the packetListening
                    log.error("No NIC to capture.");
                    log.warn("Disabling packet capture.");
                }
                catch (IOException | NotOpenException | PcapNativeException e)
                {
                    log.error("An issue happened while selecting the network interface.", e);
                    log.warn("Disabling packet capture.");
                }
                catch (Exception e)
                {
                    log.error("An unexpected error occurred while setting up the Packet Listener:", e);
                    log.warn("Disabling packet capture");
                }

            }
            else
            {
                log.warn("No NIC provided in the configuration file. Disabling packet capture.");
            }
        }

        // 2. Setup the ports for the proxy
        log.info("Configuring TCP Proxy...");
        mProxy.setRemoteIP(mConfig.get("SDNControllerIP"))
                .setListeningPort(mConfig.getInt("SDNSwitchPort", Configuration.DFLT_SDN_SWITCH_PORT))
                .setRemotePort(mConfig.getInt("SDNControllerOpenflowPort", Configuration.DFLT_SDN_CTRL_OF_PORT))
                .setProxyHandler(this.mPacketFuzzer);
        log.info("Starting TCP proxy.");
        mThreadPool.execute(mProxy);
    }

    /**
     * Stops the Core
     */
    public void stop()
    {
        // Stops the listener Listener
        if (mListener.isRunning())
        {
            log.info("Stopping Packet Listener");
            mListener.stop();
        }

        // Stops the proxy
        if (mProxy.isRunning())
        {
            log.info("Stopping TCP Proxy");
            mProxy.stop();
        }

        // Close the threads
        try
        {
            mThreadPool.shutdown();
            StopWatch watch = new StopWatch();
            watch.start();
            log.debug("Awaiting Core's threads termination...");
            if (!mThreadPool.awaitTermination(EXIT_TIMEOUT, TimeUnit.MILLISECONDS))
            {
                watch.stop();
                log.warn("Some threads in the Core's thread pool ({}@{}) have not terminated under {} ms",
                        mThreadPool.getClass().getSimpleName(),
                        mThreadPool.hashCode(),
                        EXIT_TIMEOUT);

                mThreadPool.shutdownNow();
            }
            else
            {
                watch.stop();
                log.debug("Core's threads terminated in {} ns", watch.getTime(TimeUnit.NANOSECONDS));
            }
        }
        catch (InterruptedException e)
        {
            log.debug("{} has been interrupted while exiting", getClass().getSimpleName());
            // (Re-)Cancel if current thread also interrupted
            mThreadPool.shutdownNow();
            // Preserve interrupt status
            Thread.currentThread().interrupt();
        }

        log.info("{} is stopped", getClass().getSimpleName());
    }

}
