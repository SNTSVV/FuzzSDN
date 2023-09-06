package edu.svv.fuzzsdn.common.network;

import org.apache.http.HttpResponse;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.client.HttpClients;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.UnknownHostException;

/**
 * A generic REST client based on {@code HttpClient}.
 */
public class RestClient
{
    public enum ContentType
    {
        ALL         ("*/*"),
        JSON        ("application/json"),
        XML         ("application/xml"),
        HTML        ("text/html"),
        PLAIN_TEXT  ("text/plain");

        private final String value;

        ContentType(String value)
        {
            this.value = value;
        }

    }

    private static final Logger log = LoggerFactory.getLogger(RestClient.class);

    private final HttpClientBuilder mHttpClientBuilder;
    private CloseableHttpClient     mHttpClient;

    // Parameters used by requests
    private boolean mRebuildClient;
    private String mBaseUrl;
    private ContentType mAcceptedContentType;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Basic Constructor for RestClient
     */
    public RestClient()
    {
        // Store Http client builder
        this.mHttpClientBuilder = HttpClients.custom();
        this.mAcceptedContentType = ContentType.ALL;
        this.mRebuildClient = true; // Set to true so it's build at least once
    }

    // ===== ( Getters ) ===============================================================================================

    public String getBaseUrl()
    {
        return this.mBaseUrl;
    }

    public HttpClient getClient()
    {
        if (mRebuildClient)
        {
            mHttpClient = mHttpClientBuilder.build();
            mRebuildClient = false;
        }

        return this.mHttpClient;
    }

    // ===== ( Setters ) ===============================================================================================

    public RestClient setBaseUrl(String bUrl)
    {
        log.info("Set Rest Client base url to: {}", bUrl);
        this.mBaseUrl = bUrl;
        return this;
    }

    public RestClient setAcceptedContentType(ContentType type)
    {
        log.info("Set Rest Client \"accept\" header to \"{}\"", type.value);
        this.mAcceptedContentType = type;
        return this;
    }

    public RestClient setCredentials(String userName, String password)
    {

        // Set the credentials
        if (userName == null || password == null)
        {
            throw new IllegalArgumentException("userName and password should not be null be filled of left null");
        }
        else
        {
            log.info("Setting up http credentials.");
            log.debug("user: \"{}\" , password: \"{}\"", userName, password);
            CredentialsProvider provider = new BasicCredentialsProvider();
            UsernamePasswordCredentials credentials = new UsernamePasswordCredentials(userName, password);
            provider.setCredentials(AuthScope.ANY, credentials);
            mHttpClientBuilder.setDefaultCredentialsProvider(provider);

            // Http Client must be rebuilt for next request
            mRebuildClient = true;
        }

        return this;
    }

    // ===== ( Public Methods ) ========================================================================================

    /**
     * Issue a RESTful GET request to the server
     *
     * @param request The filed we want to retrieve
     * @return        The answer from the server.
     */
    public String get(String request)
    {
        HttpResponse response;
        String bufString;
        StringBuilder sb = new StringBuilder();

        // Rebuild client if needed
        if (mRebuildClient)
        {
            this.mHttpClient = this.mHttpClientBuilder.build();
            mRebuildClient = false;
        }

        try
        {
            // Define request
            HttpGet getRequest = new HttpGet(this.mBaseUrl + request);
            getRequest.addHeader("accept", mAcceptedContentType.value);
            log.info("Executing GET Request: {}", getRequest.toString());

            // Get response
            response = mHttpClient.execute(getRequest);
            if (response.getStatusLine().getStatusCode() != 200)
            {
                log.warn("Failed : HTTP error code : {} ", response.getStatusLine().getStatusCode());
            }
            else
            {
                BufferedReader br = new BufferedReader(new InputStreamReader((response.getEntity().getContent())));

                while ((bufString = br.readLine()) != null)
                    sb.append(bufString);

                log.trace("Server raw output: {}", sb.toString());
            }
        }
        catch (UnknownHostException uhe)
        {
            log.error("Unknown host \"{}\"", uhe.getMessage());
        }
        catch (IOException ioe)
        {
            log.error("An error happened while executing get HttpRequest", ioe);
        }

        return sb.toString();
    }

}

