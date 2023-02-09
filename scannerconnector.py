#!/usr/local/bin/python
# -*- coding: utf-8 -*-

'''
****************************************
* Import
****************************************
'''
import os
import abc
# MYSQL database connection
import mysql.connector
from mysql.connector import Error
# logging
import logging

'''
****************************************
* Global variables
****************************************
'''
log = logging.getLogger(__name__)

'''
****************************************
* Classes
****************************************
'''
class DbConnector():
    def __init__(self, host, db_name, username, password, port=3306):
        self._db_connection = None
        self._host = host
        self._port = port
        self._db_name = db_name
        self._username = username
        self._password = password

    def __del__(self):
        self._disconnect()

    def _connect(self):
        try:
            # only create new connection, if not already a connection was created before
            if self._db_connection is None:
                self._db_connection = mysql.connector.connect(
                    host = self._host,
                    port = self._port,
                    user = self._username,
                    passwd = self._password,
                    database = self._db_name
                )
                log.debug(f"DbConnector: SQL db connected successfully")
        except Error as e:
            log.error("DbConnector: SQL connection error.")
            log.exception("Exception info:")
        return self._db_connection

    def _disconnect(self):
        if self._db_connection is not None:
            self._db_connection.close()
            self._db_connection = None
    
    def execute_query(self, query, commit=False, disconnect=True):
        result = None
        try:
            connection = self._connect()
            cursor = connection.cursor(dictionary=True)
            log.debug(f"DbConnector: SQL query '{query}'...")
            cursor.execute(query)
            if commit:
                result = connection.commit()
            else:
                result = cursor.fetchall()
            if disconnect:
                self._disconnect()
            log.debug(f"DbConnector: SQL query successfully executed")
            log.debug(f"DbConnector: SQL query result: {result}")
        except Error as e:
            log.error("DbConnector: SQL query error.")
            log.exception("Exception info:")
            self._disconnect()
            return None
        
        return result


class ScannerConnector(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def reset_all_quests(self):
        pass

    @abc.abstractmethod
    def reset_all_pokemon(self):
        pass
    
    @abc.abstractmethod
    def reset_filtered_pokemon(self, eventchange_datetime_UTC):
        pass

    @abc.abstractmethod
    def get_events(self):
        pass

    @abc.abstractmethod
    def insert_event(self, event_type_name):
        pass

    @abc.abstractmethod
    def update_event(self, event_type_name, event_start, event_end, event_lure_duration):
        pass

    @abc.abstractmethod
    def delete_event(self, event_type_name):
        pass

    @abc.abstractmethod
    def trigger_rescan(self):
        pass

class MadConnector(ScannerConnector):
    def __init__(self, db_host, db_port, db_name, db_username, db_password, rescan_trigger_command):
        self._dbconnector = DbConnector(host=db_host, port=db_port, db_name=db_name, username=db_username, password=db_password)
        self._rescan_trigger_command = rescan_trigger_command
    
    def reset_all_quests(self):
        sql_query = "TRUNCATE trs_quest"
        dbreturn = self._dbconnector.execute_query(sql_query, commit=True)
        log.info(f'MadConnector: quests deleted by SQL query: {sql_query} return: {dbreturn}')
    
    def reset_all_pokemon(self):
        sql_query = "TRUNCATE pokemon"
        dbreturn = self._dbconnector.execute_query(sql_query, commit=True)
        log.info(f'MadConnector: all pokemon deleted by SQL query: {sql_query} return: {dbreturn}')
    
    def reset_filtered_pokemon(self, eventchange_datetime_UTC):
        # SQL query: delete mon
        eventchange_timestamp = eventchange_datetime_UTC.strftime("%Y-%m-%d %H:%M:%S")
        sql_query = f"DELETE FROM pokemon WHERE last_modified < '{eventchange_timestamp}' AND disappear_time > '{eventchange_timestamp}'"
        dbreturn = self._dbconnector.execute_query(sql_query, commit=True)
        log.info(f'MadConnector: filtered pokemon deleted by SQL query: {sql_query} return: {dbreturn}')
    
    def get_events(self):
        log.info(f"MadConnector: get event")
        sql_query = "SELECT event_name, event_start, event_end FROM trs_event;"
        db_events = self._dbconnector.execute_query(sql_query)
        return db_events
    
    def insert_event(self, event_type_name, event_start, event_end, event_lure_duration):
        log.info(f"MadConnector: insert event {event_type_name} with start:{event_start}, end:{event_end}, lure_duration:{event_lure_duration}")
        sql_query = f"INSERT INTO trs_event (event_name, event_start, event_end, event_lure_duration) VALUES('{event_type_name}', '{event_start}', '{event_end}', {event_lure_duration});"
        self._dbconnector.execute_query(sql_query, commit=True)
    
    def update_event(self, event_type_name, event_start, event_end, event_lure_duration):
        log.info(f"MadConnector: updated event {event_type_name} with start:{event_start}, end:{event_end}, lure_duration:{event_lure_duration}")
        sql_query = f"UPDATE trs_event SET event_start='{event_start}', event_end='{event_end}', event_lure_duration={event_lure_duration} WHERE event_name = '{event_type_name}';"
        self._dbconnector.execute_query(sql_query, commit=True)
    
    def delete_event(self, event_type_name):
        log.info(f"MadConnector: deleted event {event_type_name}")
        sql_query = f"DELETE FROM trs_event WHERE event_name='{event_type_name}';"
        self._dbconnector.execute_query(sql_query, commit=True)
    
    def trigger_rescan(self):
        log.info("MadConnector: trigger rescan by rescan trigger command")
        try:
            exit_code = os.system(self._rescan_trigger_command)
            if exit_code != 0:
                log.error(f"run rescan trigger command '{self._rescan_trigger_command}' failed with exit code:{exit_code}")
            else:
                log.debug(f"run rescan trigger command '{self._rescan_trigger_command}' successfully")
        except Exception as e:
            log.error("MadConnector: error while running rescan trigger command '{self._rescan_trigger_command}'")
            log.exception("Exception info:") 