package edu.svv.fuzzsdn.common.network.tcpproxy;

import java.io.InputStream;
import java.io.OutputStream;

/**
 * Any object implementing this interface can handle a {@link TCPProxy} {@link InputStream} and {@link OutputStream}.
 * Meaning the object can interpret the data, modify it or even not relaying it to the output stream.
 */
public interface ProxyHandler
{
    /**
     * Callback method called by the {@link ProxyTunnel} when a proxy connection is established.
     *
     * @param in  the {@link InputStream} of the proxy tunnel.
     * @param out the {@link OutputStream} of the proxy tunnel.
     */
    void onData(InputStream in, OutputStream out);
}
