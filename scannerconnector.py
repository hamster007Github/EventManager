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
# url handling
import requests
from requests.auth import HTTPBasicAuth
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
    def __init__(self, db_host, db_port, db_name, db_username, db_password, reload_port_list = None, rescan_trigger_command = None):
        self._dbconnector = DbConnector(host=db_host, port=db_port, db_name=db_name, username=db_username, password=db_password)
        self._reload_port_list = reload_port_list
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
        # call apply_settings, if trigger ports are set
        if self._reload_port_list is not None:
            for trigger_port in self._reload_port_list:
                try:
                    reload_url = f"http://localhost:{trigger_port}/reload"
                    result = requests.get(reload_url)
                    if (result.status_code != 200) and (result.status_code != 302):
                        log.error(f"MadConnector: trigger madmin reload ('apply_settings') for configurated port: '{trigger_port}' failed with status-code {result.status_code}")
                    else:
                        log.info(f"MadConnector: triggered madmin reload ('apply_settings') for configurated port '{trigger_port}' successful")
                except requests.ConnectionError:
                    log.error(f"MadConnector: connection error for reload url '{reload_url}'. Please check your 'rescan_trigger_madmin_ports' settings or availability of madmin.")
                except Exception:
                    log.error(f"MadConnector: exception while trigger madmin reload ('apply_settings') for configurated port: '{trigger_port}'")
                    log.exception("Exception info:")
        # call usercommand/userscript, if configurated
        if self._rescan_trigger_command is not None:
            try:
                exit_code = os.system(self._rescan_trigger_command)
                if exit_code != 0:
                    log.error(f"run rescan trigger command '{self._rescan_trigger_command}' failed with exit code:{exit_code}")
                else:
                    log.info(f"run rescan trigger command '{self._rescan_trigger_command}' successfully")
            except Exception:
                log.error(f"MadConnector: exception while running rescan trigger command '{self._rescan_trigger_command}'")
                log.exception("Exception info:")

class RdmConnector(ScannerConnector):
    def __init__(self, api_url, api_username, api_password, assignment_group, rescan_trigger_command = None):
        self._api_url = api_url
        self._api_auth = HTTPBasicAuth(api_username, api_password)
        self._assignment_group = assignment_group
        self._rescan_trigger_command = rescan_trigger_command

    def _api_set_request(self, api_parameter_str):
        result = False
        try:
            url = self._api_url + "/api/set_data?" + api_parameter_str
            result = requests.get(url, auth=self._api_auth)
            if (result.status_code != 200):
                log.error(f"RdmConnector: _api_set_request '{url}' failed with status-code {result.status_code}")
            else:
                log.debug(f"RdmConnector: _api_set_request '{url}' successful. Result:{result}")
                result = True;
        except requests.ConnectionError:
            log.error(f"RdmConnector: connection error for _api_set_request '{url}'. Please check your 'rdm_api_url', 'rdm_api_username' and 'rdm_api_password' settings or availability of RDM.")
        except Exception:
            log.error(f"RdmConnector: exception while _api_set_request '{url}'")
            log.exception("Exception info:")
        return result

    def reset_all_quests(self):
        request_parameter = "clear_all_quests=true"
        if self._api_set_request(request_parameter):
            log.info(f'RdmConnector: quests deleted by API successful')
        else:
            log.error(f'RdmConnector: quests deleted by API failed')

    def reset_all_pokemon(self):
        log.info(f"RdmConnector: reset_all_pokemon not supported yet -> skip")

    def reset_filtered_pokemon(self, eventchange_datetime_UTC):
        log.info(f"RdmConnector: reset_filtered_pokemon not supported yet -> skip")

    def get_events(self):
        log.debug(f"RdmConnector: get_events not supported -> skip")
        return {}

    def insert_event(self, event_type_name, event_start, event_end, event_lure_duration):
        log.debug(f"RdmConnector: insert_event not supported -> skip")

    def update_event(self, event_type_name, event_start, event_end, event_lure_duration):
        log.debug(f"RdmConnector: update_event not supported -> skip")

    def delete_event(self, event_type_name):
        log.debug(f"RdmConnector: delete_event not supported -> skip")

    def trigger_rescan(self):
        # start re-quest assigment group
        request_parameter = f"assignmentgroup_start=true&assignmentgroup_name={self._assignment_group}"
        if self._api_set_request(request_parameter):
            log.info(f'RdmConnector: start re-quest by API start assignment group "{self._assignment_group}" successful')
        else:
            log.error(f'RdmConnector: start re-quest by API start assignment group "{self._assignment_group}" failed')
        # call usercommand/userscript, if configurated
        if self._rescan_trigger_command is not None:
            try:
                exit_code = os.system(self._rescan_trigger_command)
                if exit_code != 0:
                    log.error(f"run rescan trigger command '{self._rescan_trigger_command}' failed with exit code:{exit_code}")
                else:
                    log.info(f"run rescan trigger command '{self._rescan_trigger_command}' successfully")
            except Exception:
                log.error(f"RdmConnector: exception while running rescan trigger command '{self._rescan_trigger_command}'")
                log.exception("Exception info:")

class GolbathybridConnector(ScannerConnector):
    def __init__(self, rdm_api_url, rdm_api_username, rdm_api_password, rdm_assignment_group, golbat_api_url, golbat_api_secret, rescan_trigger_command = None):
        self._golbat_api_url = golbat_api_url
        self._golbat_api_secret_ = golbat_api_secret
        self._rdmConnector = RdmConnector(rdm_api_url, rdm_api_username, rdm_api_password, rdm_assignment_group, rescan_trigger_command)

    def _api_post(self, api_url_substring, json_data):
        result = False
        try:
            url = self._golbat_api_url + api_url_substring
            html_secret_header = f"X-Golbat-Secret: {self._golbat_api_secret}"
            result = requests.post(url, headers=html_secret_header, json=json_data)
            if (result.status_code != 200):
                log.error(f"GolbathybridConnector: _api_post '{url}' failed with status-code {result.status_code}")
            else:
                log.debug(f"GolbathybridConnector: _api_post '{url}' successful. Result:{result}")
                result = True;
        except requests.ConnectionError:
            log.error(f"GolbathybridConnector: connection error for _api_post '{url}'. Please check your 'golbat_api_url' and 'golbat_api_secret' settings or availability of Golbat.")
        except Exception:
            log.error(f"GolbathybridConnector: exception while _api_post '{url}'")
            log.exception("Exception info:")
        return result

    def reset_all_quests(self):
        world_geofence = {"fence":[{"lat": -90.0,"lon": -180.0},{"lat": 90.0,"lon": -180.0},{"lat": 90.0,"lon": 180.0},{"lat": -90.0,"lon": 180.0},{"lat": -90.0,"lon": -180.0}]}
        result = self._api_post("/api/clear-quests", world_geofence)
        log.info(f'GolbathybridConnector: quests deleted by Golbat API: {result}')
        self._rdmConnector.reset_all_quests()

    def reset_all_pokemon(self):
        log.info(f"GolbathybridConnector: reset_all_pokemon not supported yet -> skip")
        self._rdmConnector.reset_all_pokemon()

    def reset_filtered_pokemon(self, eventchange_datetime_UTC):
        log.info(f"GolbathybridConnector: reset_filtered_pokemon not supported yet -> skip")

    def get_events(self):
        log.debug(f"GolbathybridConnector: get_events not supported -> skip")
        return {}

    def insert_event(self, event_type_name, event_start, event_end, event_lure_duration):
        log.debug(f"GolbathybridConnector: insert_event not supported -> skip")

    def update_event(self, event_type_name, event_start, event_end, event_lure_duration):
        log.debug(f"GolbathybridConnector: update_event not supported -> skip")

    def delete_event(self, event_type_name):
        log.debug(f"GolbathybridConnector: delete_event not supported -> skip")

    def trigger_rescan(self):
        self._rdmConnector.trigger_rescan()
