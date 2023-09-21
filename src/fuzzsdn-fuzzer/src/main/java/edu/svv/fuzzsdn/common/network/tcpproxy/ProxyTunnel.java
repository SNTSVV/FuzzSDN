package edu.svv.fuzzsdn.common.network.tcpproxy;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.net.SocketException;


/**
 * The ProxyTunnel class transfer the message from an input socket to an output socket.
 * If a ProxyHandler is provided, the input and output handling is delegated to the class implementing
 * the interface.
 */
public class ProxyTunnel implements Runnable
{
    // ===== ( Members ) ===============================================================================================

    private static final Logger log = LoggerFactory.getLogger(ProxyTunnel.class);

    private final Socket in;
    private final Socket out;

    private final ProxyHandler mProxyHandler;

    // ===== ( Constructor ) ===========================================================================================

    public ProxyTunnel(Socket in, Socket out)
    {
        this(in, out, null);
    }

    public ProxyTunnel(Socket in, Socket out, ProxyHandler proxyHandler)
    {
        this.in = in;
        this.out = out;
        this.mProxyHandler = proxyHandler;

        log.debug("New proxy tunnel {}:{} --> {}:{}",
                in.getInetAddress().getHostName(),
                in.getPort(),
                out.getInetAddress().getHostName(),
                out.getPort());
    }

    // ===== ( Methods ) ===============================================================================================

    @Override
    public void run()
    {
        try
        {
            InputStream inputStream = getInputStream();
            OutputStream outputStream = getOutputStream();

            if (inputStream == null || outputStream == null)
                return;


            if (mProxyHandler != null)
            {
                mProxyHandler.onData(inputStream, outputStream);
            }
            else
            {
                byte[] reply = new byte[4096];
                int bytesRead;

                // Because of TCP, make sure that we transfer all the packet with this loop
                while (-1 != (bytesRead = inputStream.read(reply)))
                {
                    // TODO Log in a TRACE for debug
                    // new Bytes repl
                    // String hex = Utils.bytesToHex(t_reply);
                    // log.trace("{}@{} received data: {}", this.getClass().getSimpleName(), this.hashCode(), hex);

                    outputStream.write(reply, 0, bytesRead);
                }
            }

        }
        catch (SocketException ignored) {}
        catch (Exception e)
        {
            log.error("An unexpected error occurred:", e);
        }
        finally
        {
            try
            {
                in.close();
                out.close();
            }
            catch (IOException ioe)
            {
                log.error("An error occurred while closing the InputStream/OutputStream", ioe);
            }
        }
    }


    // ===== ( Private Methods ) =======================================================================================

    private InputStream getInputStream()
    {
        InputStream toReturn = null;
        try
        {
            toReturn = in.getInputStream();
        }
        catch (IOException ioe)
        {
            log.error("An error occurred while opening the InputStream:", ioe);
        }

        return toReturn;
    }

    private OutputStream getOutputStream()
    {
        OutputStream toReturn = null;
        try
        {
            toReturn = out.getOutputStream();
        }
        catch (IOException ioe)
        {
            log.error("An error occurred while opening the OutputStream:", ioe);
        }

        return toReturn;
    }
}
