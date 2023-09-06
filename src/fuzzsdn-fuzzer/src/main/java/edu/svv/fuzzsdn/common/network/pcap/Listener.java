package edu.svv.fuzzsdn.common.network.pcap;

import org.pcap4j.core.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


/**
 * The goal of this class is to listen to the incoming packets on a given socket
 */
public class Listener implements Runnable
{
    // ===== (Constants) ===============================================================================================

    private static final int    INFINITE = -1;
    private static final String DUMP_EXTENSION = "pcap";
    private static final Logger log = LoggerFactory.getLogger(Listener.class);

    // ===== (Parameters) ==============================================================================================


    private int snapshotLength = 65536; // bytes
    private int readTimeout    = 10;    // ms
    private int maxPackets     = 50;    // nb of packets to capture in the loop

    private String  mFilter = null;
    private String  mDumpFile;
    private boolean mEnableDump;

    // Device, Handle ,Dump & Packet Receiver
    private PcapNetworkInterface    mDevice = null;
    private PcapHandle              mHandle;
    private PacketListener          mPacketListener;
    private PcapDumper              mDumper;
    private Callback                mCallback;

    // ===== ( Getters ) ===============================================================================================

    /**
     * Return a boolean that says if the packet listener is running.
     *
     * @return True if the handle is open or false otherwise
     */
    public boolean isRunning()
    {
        if (mHandle != null)
            return mHandle.isOpen();
        else
            return false;
    }

    // ===== (Setters) =================================================================================================


    public Listener setSnapshotLength(int bytes)
    {
        if (bytes >= 0)
            this.snapshotLength = bytes;
        else
            this.snapshotLength = INFINITE;
        return this;
    }

    public Listener setTimeout(int ms)
    {
        if (ms > 0)
            this.readTimeout = ms;
        else
            this.readTimeout = INFINITE;

        return this;
    }

    public Listener setMaxPackets(int nbOfPackets)
    {
        if (nbOfPackets > 0)
            this.maxPackets = nbOfPackets;
        else
            this.maxPackets = INFINITE;

        return this;
    }

    // Set the filter
    public Listener setFilter(String mFilter)
    {
        this.mFilter = mFilter;
        return this;
    }

    //
    public Listener setDumpFile(String fileName)
    {
        boolean goodExtension = false;

        // Check extension is .pcap
        int index = fileName.lastIndexOf('.');
        if (index > 0)
        {
            String extension = fileName.substring(index + 1);
            if (extension.equals(DUMP_EXTENSION))
                goodExtension = true;
        }

        if (!goodExtension)
            fileName += "." + DUMP_EXTENSION;

        mDumpFile = fileName;
        return this;
    }

    public Listener enableDump(boolean status)
    {
        mEnableDump = status;
        return this;
    }

    public Listener setNetworkDevice(PcapNetworkInterface device)
    {
        this.mDevice = device;
        return this;
    }

    public Listener setPacketReceiver(Callback callback)
    {
        this.mCallback = callback;
        return this;
    }

    // ===== (Public Methods) ==========================================================================================

    /**
     * Initialize the Packet Listener
     *
     * @throws PcapNativeException
     * @throws NotOpenException
     * @throws RuntimeException    when there is no network device set up beforehand
     */
    public void setup() throws RuntimeException, PcapNativeException, NotOpenException
    {
        // If no device is selected
        if (mDevice == null)
        {
            StringBuilder errMsg = new StringBuilder().append("No network device set up for ")
                                                      .append(getClass().getSimpleName())
                                                      .append("@")
                                                      .append(hashCode());

            log.error(errMsg.toString());
            throw new RuntimeException(errMsg.toString());
        }

        // Open the device and get a handle
        mHandle = mDevice.openLive(snapshotLength, PcapNetworkInterface.PromiscuousMode.PROMISCUOUS, readTimeout);

        // Open a dump file if enabled
        if (mEnableDump && mDumpFile != null)
        {
            mDumper = mHandle.dumpOpen(mDumpFile);
        }

        // Set a filter if the its not null
        if (mFilter != null)
            mHandle.setFilter(this.mFilter, BpfProgram.BpfCompileMode.OPTIMIZE);

        // Create a listener that defines what to do with the received packets
        mPacketListener = packet -> {
            try
            {
                // Dump the packet if there is a dumper configured
                if (mDumper != null && mEnableDump)
                    mDumper.dump(packet, mHandle.getTimestamp());

                // Call the Receiver callback if there is one
                if (mCallback != null)
                    mCallback.packetReceivedCallback(packet);
            }
            catch (NotOpenException e)
            {
                log.error("The packet listener handle is not open:", e);
            }
        };
    }

    @Override
    public void run()
    {
        // Tell the handle to loop using the listener we created
        try
        {

            mHandle.loop(maxPackets, mPacketListener);
        }
        catch (NotOpenException noe)
        {
            // The mPacketListener wasn't opened. Which imply that the setup wasn't executed properly
            log.error("{}:{} is not configured properly and thus cannot be run.", getClass().getSimpleName(), hashCode(), noe);
        }
        catch (PcapNativeException pne)
        {
            log.error("An unexpected error occurred:", pne);
        }
        catch (InterruptedException silent)
        {
            log.info("Stopping {}:{}", getClass().getSimpleName(), hashCode());
        }
    }

    public void stop()
    {
        try
        {
            if (isRunning())
            {
                mHandle.breakLoop();
                mHandle.close();
            }
        }
        catch (NotOpenException e)
        {
            log.error("Error: pcap.Listener must be in \"run\" state before being stopped.", e);
        }

        if (mDumper != null)
        {
            mDumper.close();
            mDumper = null;
        }
    }
}
