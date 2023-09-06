package edu.svv.fuzzsdn.common.sql;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class SqlDatabase
{
    private static final Logger log = LoggerFactory.getLogger(SqlDatabase.class);
    private static final String ROOT_URL = "jdbc:mysql";

    private Connection connection;
    private String address;
    private int port;
    private String database;
    private String username = "root";
    private String password = "localhost";


    // ===== ( Constructor ) ===========================================================================================

    public SqlDatabase()
    { }

    // ===== ( Getters ) ===============================================================================================

    public boolean isOpen()
    {
        try (Connection conn = this.getConnection())
        {
            return !conn.isClosed();
        }
        catch (SQLException e)
        {
            log.error("An error occurred while trying to assert connection status: ", e);
            return false;
        }
    }

    public String getUrl()
    {
        return ROOT_URL + "://" + this.address + ":" + this.port + "/" + this.database;
    }

    public Connection getConnection()
    {
        try
        {
            return DriverManager.getConnection(getUrl(), username, password);
        }
        catch (SQLException e)
        {
            log.error("An error occurred while opening the database: ", e);
        }

        return null;
    }

    // ===== ( Setters ) ===============================================================================================

    public SqlDatabase setCredentials(final String username, final String password)
    {
        this.username = username;
        this.password = password == null ? "" : password; // Set password to empty string if the password is null
        return this;
    }

    public SqlDatabase setAddress(final String address, final int port)
    {
        this.address = address;
        this.port = port;
        return this;
    }

    public SqlDatabase setDatabase(final String database)
    {
        this.database = database;
        return this;
    }

    // ===== ( Methods ) ===============================================================================================

    public boolean open()
    {
        try
        {
            this.connection = DriverManager.getConnection(getUrl(), username, password);
        }
        catch (Exception e)
        {
            log.error("An error occurred while opening the database: ", e);
        }

        return this.isOpen();
    }

    public boolean close()
    {
        try
        {
            if (this.isOpen())
                this.connection.close();
        }
        catch (Exception e)
        {
            log.error("An error occurred while closing the database: ", e);
        }

        return this.isOpen();
    }

}
