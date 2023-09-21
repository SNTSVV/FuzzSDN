package edu.svv.fuzzsdn.common.network.tcpproxy;

import org.apache.commons.lang3.time.StopWatch;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.ConnectException;
import java.net.Socket;
import java.net.UnknownHostException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class ProxyConnection implements Runnable
{
    // ===== ( Members ) ===============================================================================================

    private static final Logger log = LoggerFactory.getLogger(ProxyConnection.class);
    private static final long EXIT_TIMEOUT = 500;

    private final Socket            mClientSocket;
    private final String            mRemoteIP;
    private final int               mRemotePort;
    private final String            mClientIP;
    private final int               mClientPort;
    private Socket                  mServerSocket = null;

    private final ProxyHandler      mProxyHandler;

    private final ExecutorService mThreadPool = Executors.newFixedThreadPool(10);

    // ===== ( Constructor ) ===========================================================================================

    public ProxyConnection(Socket clientSocket, String remoteIp, int remotePort)
    {
        this(clientSocket, remoteIp, remotePort, null);
    }

    public ProxyConnection(Socket clientSocket, String remoteIp, int remotePort, ProxyHandler proxyHandler)
    {
        this.mClientSocket  = clientSocket;
        this.mRemoteIP      = remoteIp;
        this.mRemotePort    = remotePort;
        this.mClientIP      = clientSocket.getInetAddress().getHostAddress();
        this.mClientPort    = clientSocket.getPort();
        this.mProxyHandler  = proxyHandler;
    }

    // ===== ( Public Methods ) ========================================================================================

    @Override
    public void run()
    {
        try
        {
            log.debug("Connecting server socket to {}:{}", mRemoteIP, mRemotePort);
            mServerSocket = new Socket(mRemoteIP, mRemotePort);
            log.debug("Server socket to {}:{} is connected", mRemoteIP, mRemotePort);
        }
        catch (ConnectException | UnknownHostException e)
        {
            // Most common errors with socket: Server is not listening or host is unknown
            log.error("Couldn't connect server socket to {}:{} with reason: {} .", mRemoteIP, mRemotePort, e.getMessage());
            return;
        }
        catch (IOException ioe)
        {
            log.error("IOException while opening a server socket to {}:{} .", mRemoteIP, mRemotePort, ioe);
            return;
        }

        // Bi-directional proxy is connected
        log.info("Establishing bi-directional proxy connection {}:{} <-> {}:{} .", mClientIP, mClientPort, mRemoteIP, mRemotePort);
        mThreadPool.execute(new ProxyTunnel(mClientSocket, mServerSocket, mProxyHandler)); // client -> server
        mThreadPool.execute(new ProxyTunnel(mServerSocket, mClientSocket, mProxyHandler)); // server -> client

        while (!Thread.currentThread().isInterrupted())
        {
            if (mClientSocket.isClosed())
            {
                log.info("Client socket ({}:{}) closed", mClientSocket.getInetAddress().getHostName(), mClientSocket.getPort());
                closeServerConnection();
                break;
            }

            try
            {
                // TODO remove busy waiting loop
                Thread.sleep(20);
            }
            catch (InterruptedException e)
            {
                // break from the while loop
                break;
            }
        }

        this.shutdown();
        log.info("Bi-directional proxy connection {}:{} <-> {}:{} closed.", mClientIP, mClientPort, mRemoteIP, mRemotePort);

    }

    // ===== ( Private Methods) ========================================================================================

    /**
     * Closes the socket connection on the server side.
     */
    private void closeServerConnection()
    {
        if (mServerSocket != null && !mServerSocket.isClosed())
        {
            try
            {
                log.info("Closing connection to remote host ({}:{}).", mServerSocket.getInetAddress().getHostName(), mServerSocket.getPort());
                mServerSocket.close();
            }
            catch (IOException ioe)
            {
                log.error("An error occurred while closing connection to remote host ({}:{}):",
                        mServerSocket.getInetAddress().getHostName(),
                        mServerSocket.getPort(),
                        ioe);
            }
        }
    }

    /**
     * Closes the socket connection on the client side.
     */
    private void closeClientConnection()
    {
        if (mServerSocket != null && !mServerSocket.isClosed())
        {
            try
            {
                log.info("Closing connection to local host ({}:{}).", mClientSocket.getInetAddress().getHostName(), mClientSocket.getPort());
                mClientSocket.close();
            }
            catch (IOException ioe)
            {
                log.error("An error occurred while closing the connection to local host ({}:{}):",
                        mClientSocket.getInetAddress().getHostName(),
                        mClientSocket.getPort(),
                        ioe);
            }
        }
    }


    /**
     * Shutdowns routing for a Proxy connection.
     */
    private void shutdown()
    {
        // Silently close the connections
        closeClientConnection();
        closeServerConnection();

        try
        {
            mThreadPool.shutdown();
            StopWatch watch = new StopWatch();
            watch.start();
            log.debug("Awaiting {}@{}'s threads termination...", this.getClass().getName(), this.hashCode());
            if (!mThreadPool.awaitTermination(EXIT_TIMEOUT, TimeUnit.MILLISECONDS))
            {
                watch.stop();
                log.warn("Some threads in the {}#{}'s thread pool ({}@{}) have not terminated under {} ms",
                        this.getClass().getName(),
                        this.hashCode(),
                        mThreadPool.getClass().getSimpleName(),
                        mThreadPool.hashCode(),
                        EXIT_TIMEOUT);

                log.warn("Forcing shutdown. The threads might never stop and prevent proper termination.");
                mThreadPool.shutdownNow();
            }
            else
            {
                watch.stop();
                log.debug("{}#{}'s threads terminated in {} ns",
                        this.getClass().getName(),
                        this.hashCode(),
                        watch.getTime(TimeUnit.NANOSECONDS));
            }
        }
        catch (InterruptedException e1)
        {
            log.debug("{}@{} has been interrupted while exiting", this.getClass().getSimpleName(), this.hashCode());
            // (Re-)Cancel if current thread also interrupted
            mThreadPool.shutdownNow();
            // Preserve interrupt status
            Thread.currentThread().interrupt();
        }
    }
}