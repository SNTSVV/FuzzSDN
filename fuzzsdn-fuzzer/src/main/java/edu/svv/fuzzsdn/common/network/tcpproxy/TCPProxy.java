package edu.svv.fuzzsdn.common.network.tcpproxy;

import org.apache.commons.lang3.time.StopWatch;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;


public class TCPProxy implements Runnable
{
    // ===== ( Parameters ) ============================================================================================

    // Constants and statics
    private static final Logger log = LoggerFactory.getLogger(TCPProxy.class);
    private static final int EXIT_TIMEOUT = 3000; // ms

    //
    private String          mRemoteIP;
    private int             mRemotePort;
    private String          mListeningIP;
    private int             mListeningPort;
    private boolean         mIsStopped;
    private ProxyHandler    mProxyHandler;

    // Thread executor
    private final ExecutorService mThreadPool = Executors.newFixedThreadPool(100);

    // Server Socket
    private ServerSocket mServerSocket;

    // ===== ( Constructor ) ===========================================================================================

    public TCPProxy(String remoteIP, int remotePort, int port)
    {
        this(remoteIP, remotePort, port, null);
    }

    public TCPProxy(String remoteIP, int remotePort, int port, ProxyHandler proxyHandler)
    {
        this.mRemoteIP = remoteIP;
        this.mRemotePort = remotePort;
        this.mListeningPort = port;
        setProxyHandler(proxyHandler);
    }

    public TCPProxy() {}

    // ===== ( Getters ) ===============================================================================================

    public synchronized boolean isRunning()
    {
        return !this.mIsStopped;
    }

    // ===== ( Setters ) ===============================================================================================

    public TCPProxy setRemoteIP(String IP)
    {
        this.mRemoteIP = IP;
        return this;
    }

    public TCPProxy setListeningPort(int port)
    {
        this.mListeningPort = port;
        return this;
    }

    public TCPProxy setRemotePort(int port)
    {
        this.mRemotePort = port;
        return this;
    }

    public TCPProxy setProxyHandler(ProxyHandler handler)
    {
        log.debug("Handler \"{}@{}\" bound to {}@{}", handler.getClass().getSimpleName(), this.hashCode(), this.getClass().getSimpleName(), handler.hashCode());
        this.mProxyHandler = handler;
        return this;
    }

    // ===== ( Public Methods ) ========================================================================================

    @Override
    public void run()
    {
        try
        {
            mServerSocket = new ServerSocket(mListeningPort);
            mListeningIP = mServerSocket.getInetAddress().getHostName();

            log.info("Starting new TCP Proxy between {}:{} and {}:{}.", mListeningIP, mListeningPort, mRemoteIP, mRemotePort);

            while (!Thread.currentThread().isInterrupted() && !mIsStopped && !mThreadPool.isShutdown())
            {
                // Wait for new connections
                log.debug("Connecting to client ...");
                try
                {
                    Socket socket = mServerSocket.accept();

                    // Start a new thread
                    if (!mThreadPool.isShutdown())
                    {
                        log.debug("Client socket to {} is connected.", socket.getRemoteSocketAddress().toString().substring(1));
                        mThreadPool.execute(new ProxyConnection(socket, mRemoteIP, mRemotePort, mProxyHandler));
                    }
                    else
                    {
                        // close the socket before exiting the loop
                        socket.close();
                        mServerSocket.close();
                    }
                }
                catch (SocketException e)
                {
                    if (!e.getMessage().equals("Socket closed"))
                        log.error("An error occurred while opening the server socket", e);
                }
            }
        }
        catch (IOException e)
        {
            log.error("An error occurred while creating {}@{}'s server socket", getClass().getSimpleName(), hashCode());
        }
    }

    public synchronized void stop()
    {
        log.info("Stopping {}@{} ({}:{} to {}:{})",
                this.getClass().getName(),
                this.hashCode(),
                mListeningIP,
                mListeningPort,
                mRemoteIP,
                mRemotePort);

        // Set state to stopped
        mIsStopped = true;

        // Close the Server Socket
        try
        {
            if (!mServerSocket.isClosed())
            {
                log.debug("Closing {}@{}'s server socket", this.getClass().getName(), this.hashCode());
                mServerSocket.close();
            }
        }
        catch (IOException e)
        {
            log.error("An error occurred while stopping {}@{} server socket", this.getClass().getSimpleName(), this.hashCode(), e);
        }

        // Shutdown the thread pool
        log.debug("Stopping {}@{}'s thread pool...", this.getClass().getSimpleName(), this.hashCode());
        StopWatch watch = new StopWatch();
        watch.start();
        try
        {
            mThreadPool.shutdown();
            if (!mThreadPool.awaitTermination(EXIT_TIMEOUT, TimeUnit.MILLISECONDS))
            {
                log.warn("Couldn't stop {}@{} under {} ms.", this.getClass().getSimpleName(), this.hashCode(), EXIT_TIMEOUT);
                log.warn("Forcing shutdown. The threads might never stop and prevent proper termination.");
                mThreadPool.shutdownNow();
            }
            else
            {
                watch.stop();
                log.debug("{}@{}'s thread pool stopped in {} ns", this.getClass().getSimpleName(), this.hashCode(), watch.getNanoTime());
            }

        }
        catch (InterruptedException e)
        {
            // (Re-)Cancel if current thread also interrupted
            mThreadPool.shutdownNow();
            // Preserve interrupt status
            Thread.currentThread().interrupt();
        }
    }
}
