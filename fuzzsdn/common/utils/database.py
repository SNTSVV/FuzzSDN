# -*- coding: utf-8 -*-
"""
A class to manipulate all operations with a database
"""

import copy
import logging
from typing import Optional, Tuple

import mysql.connector
from mysql.connector import MySQLConnection

# ======================================================================================================================
# Module variables
# ======================================================================================================================

logger : logging.Logger = logging.getLogger(__name__)

# ======================================================================================================================
# Class Database
# ======================================================================================================================

class Database:
    """A class that handles all operations with the database."""

    # ------------------------------------------------------------------------------------------------------------------
    # Attributes
    # ------------------------------------------------------------------------------------------------------------------

    # Database parameters
    __host     : Optional[str] = None
    __user     : Optional[str] = None
    __password : Optional[str] = None
    __database : Optional[str] = None

    # Connection and cursor used by MySQLdb
    __db_connection : Optional[MySQLConnection] = None
    __db_cursor     : Optional[MySQLConnection.cursor] = None

    # Internals
    __is_init      : bool = False
    __is_connected : bool = False

    # ------------------------------------------------------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def init(cls, hostname : str, username : str, password : str, force : bool = False) -> None:
        """
        Initialize the database.

        Args:
            hostname:
                Hostname of the database
            username:
                Username to use to connect to the database
            password:
                Password to use to connect to the database
            force:
                Force the initialization even if the class is already initialized.
                Defaults to False.
        """
        if cls.__is_connected is True:
            if force is True:
                cls.disconnect()
            else:
                raise RuntimeError("Can't initialize the class when connected to a database")

        cls.__host = hostname
        cls.__user = username
        cls.__password = password

        cls.__log = logging.getLogger(__name__)
        cls.__is_init = True

        logger.debug("Database module started.")
    # End def init

    @classmethod
    def is_init(cls) -> bool:
        """Return the initialization status of the database"""
        return cls.__is_init

    @classmethod
    def reload(cls, db=None):
        """Reload the parameters from the database."""
        if cls.__is_connected is True and db is not None:
            # If we are connected, we disconnect and reconnect
            cls.init(hostname=cls.__host,
                     password=cls.__password,
                     username=cls.__user,
                     force=True)
            cls.connect(db)
        else:
            cls.init(hostname=cls.__host,
                     password=cls.__password,
                     username=cls.__user)
    # End def init

    # ------------------------------------------------------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def connect(cls, db):
        """
        Connect to the database.

        db -- Parameter specifying the database
        """
        if cls.__is_connected is True:
            cls.disconnect()

        cls.__database = db
        try:
            cls.__db_connection = mysql.connector.connect(host=cls.__host,
                                                          user=cls.__user,
                                                          password=cls.__password,
                                                          database=cls.__database)
        except Exception as e:
            logger.exception("Exception '{}' happened while connecting:".format(e))
            raise RuntimeError("Can't connect to the database")
        else:
            cls.__db_cursor = cls.__db_connection.cursor(buffered=True)
            cls.__is_connected = True
    # End def connect

    @classmethod
    def get_connection(cls, db):
        """
        Issue a new connection to the database

        :param db: name of the database
        :return: a database cursor
        """
        if cls.__is_connected is True:
            cls.disconnect()

        cls.__database = db
        try:
            connection = mysql.connector.connect(host=cls.__host,
                                                 user=cls.__user,
                                                 password=cls.__password,
                                                 database=cls.__database)
        except Exception as e:
            logger.exception("Exception '{}' happened while connecting:".format(e))
            raise RuntimeError("Can't connect to the database")
        else:
            return connection, connection.cursor(buffered=True)

    @classmethod
    def get_cursor(cls) -> Tuple[MySQLConnection, MySQLConnection.cursor]:
        """
        Return the cursor of the database
        """
        return cls.__db_cursor

    @classmethod
    def disconnect(cls):
        """
        Disconnect from the database.
        """
        if cls.__is_connected is True:
            if cls.__db_cursor is not None:
                cls.__db_cursor.close()
                cls.__db_cursor = None
            cls.__db_connection.close()
        cls.__db_connection = None
        cls.__is_connected = False
    # End def disconnect

    @classmethod
    def is_connected(cls):
        """
        Get the connection status of the db.
        """
        # We send a copy so the status can't be modified without actually disconnecting
        return copy.copy(cls.__is_connected)

    # ------------------------------------------------------------------------------------------------------------------
    # Query management
    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def execute(cls, query, parameters=None):
        """
        Execute a query and returns the arguments if necessary.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        cls.__db_cursor.execute(query, parameters or ())
        logger.debug("SQL Command: {} {}".format(query, parameters if not None else ''))
    # End def execute

    @classmethod
    def query(cls, query, parameters=None):
        """
        Execute a query, commit it and fetch all the data.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        cls.__db_cursor.execute(query, parameters or ())
        logger.debug("SQL Command: {} {}".format(query, parameters if not None else ''))
        cls.commit()

        return cls.fetchall()
    # End def query

    @classmethod
    def commit(cls):
        """
        Commit the last queries if needed.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        logger.debug("Commit last queries")
        cls.__db_connection.commit()
    # End def commit

    @classmethod
    def fetchall(cls):
        """
        Fetch all rows.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        logger.debug("Fetching all rows")
        return cls.__db_cursor.fetchall()
    # End def fetchall

    @classmethod
    def fetchone(cls):
        """
        Fetch 1 row.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        logger.debug("Fetching one row")
        return cls.__db_cursor.fetchone()
    # End def fetchone

    @classmethod
    def fetchmany(cls, size=1):
        """
        Fetch X row.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        logger.debug("Fetching one row")
        return cls.__db_cursor.fetchmany(size=size)
    # End def fetchone

    # ------------------------------------------------------------------------------------------------------------------
    # Database management
    # ------------------------------------------------------------------------------------------------------------------

    @classmethod
    def get_database(cls):
        """
        Get the name of the current database.
        """
        return copy.copy(cls.__database)

    @classmethod
    def rows(cls):
        """
        Return number of rows after a command.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        return cls.__db_cursor.rowcount
# End class Database
