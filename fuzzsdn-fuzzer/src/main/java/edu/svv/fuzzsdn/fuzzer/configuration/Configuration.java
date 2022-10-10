package edu.svv.fuzzsdn.fuzzer.configuration;

import org.apache.commons.lang3.StringUtils;
import org.apache.logging.log4j.Level;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.core.LoggerContext;
import org.apache.logging.log4j.core.config.LoggerConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.sql.Date;
import java.text.SimpleDateFormat;
import java.time.Instant;
import java.util.Properties;

/**
 * Configuration Class is a singleton class that is responsible for loading all of
 * the general configuration options for the application and dispatch them to the
 * various modules.
 */
public class Configuration
{

    // ===== ( Parameters ) ============================================================================================

    // Logger
    private static final Logger log = LoggerFactory.getLogger(Configuration.class);

    // Singleton configuration object
    private static Configuration instance = null;

    // Properties object where the setting files are read into
    private Properties properties;

    // ===== ( Default Property values ) ===============================================================================

    public static final long PID                    = ProcessHandle.current().pid();    // Process ID of the application

    public static final int DFLT_SDN_SWITCH_PORT    = 52525;                            // Port used by the application to connect with the SDN Switch
    public static final int DFLT_SDN_CTRL_OF_PORT   = 6653;                             // Port used by the SDN Controller

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Default Constructor for Configuration class
     */
    private Configuration()
    {
        // Print the log header to the log file
        printLogHeader();
        log.info("Loading configuration");

        // 1. Check if there is a user implemented configuration file
        try
        {
            this.buildFolderStructure();
            this.init();
            this.configureLogger();
        }
        catch (IOException | RuntimeException e)
        {
            // Extremely bad !, abort !!
            log.error("Impossible to initialize configuration class.", e);
            log.error("Quitting the application");
            System.exit(1);
        }
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * Get the Instance of this class There should only ever be one instance of
     * this class and other classes can use this static method to retrieve the
     * instance
     *
     * @return Configuration the stored Instance of this class
     */
    public static Configuration getInstance()
    {
        if (Configuration.instance == null)
        {
            Configuration.instance = new Configuration();
        }

        return Configuration.instance;
    }

    /**
     * Searches for the parameter with the specified key in this configuration file.
     * If the parameter is not found in the configuration file, the default value is
     * returned.
     *
     * @param key           the parameter's key
     * @param defaultValue  a default value
     * @return      the value in the configuration file
     */
    public String get(String key, String defaultValue)
    {
        String value = this.properties.getProperty(key, defaultValue);
        return StringUtils.strip(value, "\"'");
    }

    /**
     * {@code defaultValue} defaults to {@code null}
     * @see Configuration#get(String, String)
     */
    public String get(String key)
    {
        return get(key, null);
    }

    /**
     * Searches for the parameter with the specified key in this configuration file.
     * If a parameter is found, and the value is Yes | True | No | False, then value is interpreted
     * as a {@code boolean}. If the parameter is not found in the configuration file, the default value
     * {@code false} is returned
     *
     * @param key   the parameter's key
     * @return      value of the parameter as a {@code boolean}
     */
    public boolean getBoolean(String key)
    {
        String property = this.get(key);
        if (property == null)
        {
            log.warn("Key {} is null. Using false by default.", key);
            return false;
        }
        else if (property.equalsIgnoreCase("yes") || property.equalsIgnoreCase("true"))
        {
            return true;
        }
        else if (property.equalsIgnoreCase("no") || property.equalsIgnoreCase("false"))
        {
            return false;
        }
        else
        {
            log.warn("Key {} (value: {}) cannot be interpreted as a \"boolean\". Using false by default", key, property);
            return false;
        }
    }

    /**
     * Searches for the parameter with the specified key in this configuration file.
     * If a parameter is found, the value is interpreted as an {@code int}. If the parameter is not
     * found in the configuration file, or the value is not an integer, then the defaultValue is returned
     *
     * @param key           The parameter's key
     * @param defaultValue  A default value
     * @return              Value of the parameter as an {@code int}
     */
    public int getInt(String key, int defaultValue)
    {
        String property = this.get(key);
        if (property == null)
        {
            log.warn("Key \"{}\" is null. Using {} by default.", key, defaultValue);
            return defaultValue;
        }

        try
        {
            return Integer.parseInt(property);
        }
        catch (NumberFormatException nfe)
        {
            log.warn("Key \"{}\" (value: {}) cannot be interpreted as a \"int\". Using \"{}\" by default", key, property, defaultValue);
            return defaultValue;
        }
    }

    /**
     * {@code defaultValue} defaults to {@link Integer#MIN_VALUE}
     * @see Configuration#getInt(String, int)
     */
    public int getInt(String key)
    {
        String property = this.get(key);
        if (property == null)
        {
            log.warn("Key \"{}\" is null. Using {} by default.", key, Integer.MIN_VALUE);
            return Integer.MIN_VALUE;
        }

        try
        {
            return Integer.parseInt(property);
        }
        catch (NumberFormatException nfe)
        {
            log.warn("Key \"{}\" (value: {}) cannot be interpreted as a \"int\". Using \"{}\" by default", key, property, Integer.MIN_VALUE);
            return Integer.MIN_VALUE;
        }
    }

    // ===== ( Setters ) ===============================================================================================

    /**
     * Change the value of one of the key for the current application.
     * Changes are not saved in the configuration file
     *
     * @param key   name of the parameter
     * @param value value to set the parameter at
     * @return      the Configuration object, so calls can be chained
     */
    public Configuration set(String key, String value)
    {
        this.properties.setProperty(key, value);
        return this;
    }

    // ===== ( Private Methods ) =======================================================================================


    private void buildFolderStructure()
    {
        // Build config directory
        System.out.println(AppPaths.userLogDir().toAbsolutePath());
        System.out.println(AppPaths.userConfigFile());
        File dir = new File(AppPaths.userConfigDir().toAbsolutePath().toString());
        boolean success;
        if (!dir.exists())
        {
            success = dir.mkdirs();
            System.out.println(success);
        }
    }

    /**
     * Initialize the configuration with the specified file.
     * If the file doesn't exist, fall back to a default configuration file.
     * @throws IOException when neither the default of user-defined configuration file can be found
     */
    private void init() throws IOException
    {
        this.properties = new java.util.Properties();
        try
        {

            log.debug("Loading configuration file...");
            this.properties.load(new FileInputStream(AppPaths.userConfigFile().toAbsolutePath().toString()));
        }
        catch (IOException e)
        {
            // If an error happens on the default file, just re-throw the original ioe exception to abort the
            // application
            log.error("Couldn't load the configuration file.");
            throw e;
        }
    }

    /**
     * (Re-)Configure the logging module depending on the parameters of the configuration file
     */
    private void configureLogger()
    {
        // 1. Adjust log level depending on the configuration
        // Get logger context
        final LoggerContext ctx = (LoggerContext) LogManager.getContext(false);
        org.apache.logging.log4j.core.config.Configuration config = ctx.getConfiguration();

        // Change general log level
        Level logLevel = Level.toLevel(get("FileLogLevel"), Level.INFO);
        LoggerConfig loggerConfig = config.getLoggers().get("edu.svv.fuzzsdn.fuzzer");
        loggerConfig.removeAppender("rolling_file");
        loggerConfig.addAppender(config.getAppender("rolling_file"), logLevel, null);

        // Change console log level
        Level consoleLogLevel = Level.toLevel(get("ConsoleLogLevel"), Level.WARN);
        loggerConfig.removeAppender("console");
        loggerConfig.addAppender(config.getAppender("console"), consoleLogLevel, null);

        // Update log level
        ctx.updateLoggers();
    }

    private void printLogHeader()
    {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
        StringBuilder headerString = new StringBuilder();
        headerString.append("#".repeat(100)).append("\n");
        headerString.append("App Name   : Control Flow Fuzzer v0.2").append("\n");
        headerString.append("PID        : ").append(PID).append("\n");
        headerString.append("Start Date : ").append(sdf.format(Date.from(Instant.now()))).append("\n");
        headerString.append("=".repeat(100)).append("\n");

        // TODO use the log path from log4j2.xml
        File file = new File(AppPaths.userLogDir().resolve("fuzzsdn-fuzzer.log").toAbsolutePath().toString());
        try (FileWriter fw = new FileWriter(file))
        {
            fw.write(headerString.toString());
        }
        catch (IOException e)
        {
            log.error("Couldn't write header to log file.");
        }
    }
}

