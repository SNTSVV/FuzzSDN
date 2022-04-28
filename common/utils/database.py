#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A class to manipulate all operations with a database
"""

import copy
import logging
from typing import Optional

import MySQLdb
from MySQLdb.connections import Connection
from MySQLdb.cursors import Cursor


class Database:
    """A class that handles all operations with the database."""

    # Database parameters
    __host = None
    __user = None
    __password = None
    __database = None

    # Connection and cursor used by MySQLdb
    __db_connection : Optional[Connection]  = None
    __db_cursor     : Optional[Cursor]  = None

    # Internals
    __is_init = False
    __is_connected = False
    __log = None

    @classmethod
    def init(cls, hostname, username, password, force=False):
        """
        Initialize the database.
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
        cls.__log.debug("Database module started.")

        cls.__is_init = True

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

    # =====( Connection / Disconnection )========================================= #

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
            cls.__db_connection = MySQLdb.connect(cls.__host,
                                                  cls.__user,
                                                  cls.__password,
                                                  cls.__database)
        except Exception as e:
            cls.__log.exception("Exception '{}' happened while connecting:".format(e))
            raise RuntimeError("Can't connect to the database")
        else:
            cls.__db_cursor = cls.__db_connection.cursor()
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
            connection = MySQLdb.connect(cls.__host,
                                         cls.__user,
                                         cls.__password,
                                         cls.__database)
        except Exception as e:
            cls.__log.exception("Exception '{}' happened while connecting:".format(e))
            raise RuntimeError("Can't connect to the database")
        else:
            return connection, connection.cursor()

    @classmethod
    def get_cursor(cls):
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

    # ====( Database operations )================================================= #

    @classmethod
    def execute(cls, query, parameters=None):
        """
        Execute a query and returns the arguments if necessary.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        cls.__db_cursor.execute(query, parameters or ())
        cls.__log.debug("SQL Command: {} {}".format(query, parameters if not None else ''))
    # End def execute

    @classmethod
    def query(cls, query, parameters=None):
        """
        Execute a query, commit it and fetch all the data.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        cls.__db_cursor.execute(query, parameters or ())
        cls.__log.debug("SQL Command: {} {}".format(query, parameters if not None else ''))
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

        cls.__log.debug("Commit last queries")
        cls.__db_connection.commit()
    # End def commit

    @classmethod
    def fetchall(cls):
        """
        Fetch all rows.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        cls.__log.debug("Fetching all rows")
        return cls.__db_cursor.fetchall()
    # End def fetchall

    @classmethod
    def fetchone(cls):
        """
        Fetch 1 row.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        cls.__log.debug("Fetching one row")
        return cls.__db_cursor.fetchone()
    # End def fetchone

    @classmethod
    def fetchmany(cls, size=1):
        """
        Fetch X row.
        """
        if cls.__is_connected is False:
            raise RuntimeError("Not connected to any database")

        cls.__log.debug("Fetching one row")
        return cls.__db_cursor.fetchmany(size=size)
    # End def fetchone

    # =====( Operators )========================================================== #

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
