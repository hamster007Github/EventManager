#!/usr/local/bin/python
# -*- coding: utf-8 -*-

'''
****************************************
* Import
****************************************
'''
# os functions (path, ...)
import os
import sys
# url handling
import urllib
import requests
# .ini and json parser
import configparser
import json
# time handling
import time
from datetime import datetime, timedelta
# MYSQL database connection
import mysql.connector
from mysql.connector import Error
# logging
import logging
from logging.handlers import RotatingFileHandler
# other
import abc
import re
from string import Template

'''
****************************************
* Constants
****************************************
'''
DEFAULT_LURE_DURATION = 30
DEFAULT_TIME = datetime(2030, 1, 1, 0, 0, 0)

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

class SimpleTelegramApi:
    def __init__(self, api_token):
        self._base_url = self._get_base_url(api_token)

    def _get_base_url(self, api_token):
        return "https://api.telegram.org/bot{}/".format(api_token)

    def _send_request(self, command):
        request_url = self._base_url + command
        response = requests.get(request_url)
        decoded_response = response.content.decode("utf8")
        return decoded_response

    def send_message(self, chat_id, text, parse_mode="HTML"):
        text = urllib.parse.quote_plus(text)
        response = self._send_request("sendMessage?text={}&chat_id={}&parse_mode={}".format(text, chat_id, parse_mode))
        response = json.loads(response)
        return response

    def edit_message(self, chat_id, message_id, text, parse_mode="HTML"):
        text = urllib.parse.quote_plus(text)
        response = self._send_request("editMessageText?chat_id={}&message_id={}&parse_mode={}&text={}".format(chat_id, message_id, parse_mode, text))
        response = json.loads(response)
        # if you edit a message with the same text, you will get 'error_code': 400, 'description': 'Bad Request: message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message'
        return response

    def delete_message(self, chat_id, message_id):
        response = self._send_request("deleteMessage?chat_id={}&message_id={}".format(chat_id, message_id))
        response = json.loads(response)
        return response

    def pin_message(self, chat_id, message_id, disable_notification="True"):
        response = self._send_request("pinChatMessage?chat_id={}&message_id={}&disable_notification={}".format(chat_id, message_id, disable_notification))
        response = json.loads(response)
        return response

    def get_message(self):
        response = self._send_request("getUpdates")
        response = json.loads(response)
        return response


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
        sql_args = None
        dbreturn = self._dbconnector.execute_query(sql_query, commit=True)
        log.info(f'MadConnector: all pokemon deleted by SQL query: {sql_query} arguments: {sql_args} return: {dbreturn}')
    
    def reset_filtered_pokemon(self, eventchange_datetime_UTC):
        # SQL query: delete mon
        eventchange_timestamp = eventchange_datetime_UTC.strftime("%Y-%m-%d %H:%M:%S")
        sql_query = f"DELETE FROM pokemon WHERE last_modified < {eventchange_timestamp} AND disappear_time > {eventchange_timestamp}"
        dbreturn = self._dbconnector.execute_query(sql_query, commit=True)
        log.info(f'MadConnector: filtered pokemon deleted by SQL query: {sql_query} arguments: {sql_args} return: {dbreturn}')
    
    def get_events(self):
        log.info(f"MadConnector: get event")
        sql_query = "SELECT event_name, event_start, event_end FROM trs_event;"
        db_events = self._dbconnector.execute_query(sql_query)
        return db_events
    
    def insert_event(self, event_type_name):
        log.info(f"MadConnector: insert event {event_type_name} with default data")
        sql_query = f"INSERT INTO trs_event (event_name, event_start, event_end, event_lure_duration) VALUES('{event_type_name}', '{DEFAULT_TIME}', '{DEFAULT_TIME}', {DEFAULT_LURE_DURATION});"
        self._dbconnector.execute_query(sql_query, commit=True)
    
    def update_event(self, event_type_name, event_start, event_end, event_lure_duration):
        log.info(f'MadConnector: updated event {event_type_name} with start:{event_start}, end:{event_end}, lure_duration:{event_lure_duration}')
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

class PoGoEvent():
    def __init__(self, event_name, event_type, start_datetime, end_datetime, has_spawnpoints, has_quests, has_pokemon, bonus_lure_duration = None):
        self.name = event_name
        self.etype = event_type
        self.start = start_datetime
        self.end = end_datetime
        self.has_spawnpoints = has_spawnpoints
        self.has_quests = has_quests
        self.has_pokemon = has_pokemon
        self.bonus_lure_duration = bonus_lure_duration

    def get_dict(self):
        event_as_dict = {
            "name":f"{self.name}",
            "etype":f"{self.etype}",
            "start":f"{self.start}",
            "end":f"{self.end}",
            "has_spawnpoints":self.has_spawnpoints,
            "has_quests":self.has_quests,
            "has_pokemon":self.has_pokemon,
            "bonus_lure_duration":self.bonus_lure_duration
            }
        return event_as_dict

    @classmethod
    def fromPogoinfo(cls, raw_event):
        try:
            #check for valid input, unknown eventstart (=None) is accepted
            if raw_event["type"] is None or raw_event["end"] is None:
                return None

            # if event is added after eventstart to pogoinfo, start is Null
            bonus_lure_duration = None
            has_pokemon = False  
            event_type = raw_event["type"]

            # convert times to datetimes (pogoinfo provide local times)
            # handle unknown eventstart
            if raw_event["start"] is not None:
                start = datetime.strptime(raw_event["start"], "%Y-%m-%d %H:%M")
            else:
                start = None
            end = datetime.strptime(raw_event["end"], "%Y-%m-%d %H:%M")
            if end is None:
                return None

            # get bonus lure duration time
            bonus_lure_duration = None
            for bonus in raw_event["bonuses"]:
                if bonus.get("template", "") == "longer-lure":
                    # if lure duration is not avaiable: use default 3 hours
                    lure_duration_in_hour =  bonus.get("value", 3)
                    bonus_lure_duration = lure_duration_in_hour*60
                    break

            # check for changed pokemon spawn pool
            if raw_event["type"] == 'spotlight-hour' or raw_event["type"] == 'community-day' or raw_event["spawns"]:
                has_pokemon = True
            return cls(raw_event["name"], event_type, start, end, raw_event["has_spawnpoints"], raw_event["has_quests"], has_pokemon, bonus_lure_duration)
        except Exception as e:
            log.error("PoGoEvent.fromPogoinfo: error in creating new PoGoEvent object.")
            log.exception("Exception info:")
            return None

    def check_event_start(self, timewindow_start, timewindow_end):
        #handle unknown start
        if self.start is None:
            return False
        if timewindow_start < self.start <= timewindow_end:
            return True
        else:
            return False

    def check_event_end(self, timewindow_start, timewindow_end):
        if timewindow_start < self.end <= timewindow_end:
            return True
        else:
            return False

class PogoInfoEventList():
    def __init__(self, source_url = "https://raw.githubusercontent.com/ccev/pogoinfo/v2/active/events.json"):
        self._source_url = source_url
    def get_json(self):
        try:
            result = requests.get(self._source_url)
            json_list = result.json()
        except Exception as e:
            log.error(f"Exception in getting event list from '{self._source_url}'")
            log.exception("Exception info:")
            json_list = {}
        return json_list

class EventManager():
    def __init__(self, config_file_name = "/config/config.ini"):
        self._rootdir = os.path.dirname(os.path.abspath(__file__))
        self._config = configparser.ConfigParser()
        self._config.read(self._rootdir + config_file_name)
        self._local = None
        try:
            f = open(self._rootdir + "/config/local_custom.json")
            self._local = json.loads(f.read())
            log.info("init: loaded local_custom.json")
            f.close()
        except:
            log.warning("init: failed loading local_custom.json. Fallback to local_default.json")
            f = open(self._rootdir + "/config/local_default.json")
            self._local = json.loads(f.read())
            f.close()
        
        self.type_to_name = {
            "community-day": "Community Days",
            "spotlight-hour": "Spotlight Hours",
            "event": "Regular Events",
            "default": "DEFAULT",
            "?": "Others"
        }
        self._last_pokemon_reset_check = helper_time_now()
        self._last_quest_reset_check = helper_time_now()
        self._last_event_update = datetime(2000, 1, 1, 0, 0, 0)

        self.tz_offset = round((helper_time_now() - datetime.utcnow()).total_seconds() / 3600)
        self._load_config_parameter()

    def _load_config_parameter(self):
        # section [general]: general settings
        self.__sleep = self._config.getint("general", "sleep", fallback=3600)
        self.__sleep_mainloop_in_s = 60
        self.__delete_events = self._config.getboolean("general", "delete_events", fallback=False)
        self.__language = self._config.get("general", "language", fallback="en").strip()
        self.__eventcache_path = self._config.get("general", "custom_eventcache_path", fallback="").strip()
        # pokemon reset configuration parameter
        self.__reset_pokemon_enable = self._config.getboolean("general", "reset_pokemon_enable", fallback=False)
        self.__reset_pokemon_strategy = self._config.get("general", "reset_pokemon_strategy", fallback="all").strip()
        self.__reset_pokemon_restart_app = self._config.getboolean("general", "reset_pokemon_restart_app", fallback=False)
        # quest reset configuration parameter
        self.__reset_quests_enable = self._config.getboolean("general", "reset_quests_enable", fallback=False)
        reset_for = self._config.get("general", "reset_quests_event_type", fallback="event")
        self.__quests_reset_types = {}
        for etype in reset_for.split(" "):
            etype = etype.strip()
            if ":" in etype:
                split = etype.split(":")
                etype = split[0]
                if "start" in split[1]:
                    times = ["start"]
                elif "end" in split[1]:
                    times = ["end"]
                else:
                    times = ["start", "end"]
            else:
                times = ["start", "end"]
            self.__quests_reset_types[etype] = times
        quests_reset_excludes_str = self._config.get("general", "reset_quests_exclude_events", fallback=None)
        if quests_reset_excludes_str is None:
            self.__quests_reset_excludes_list = None
        else:
            self.__quests_reset_excludes_list = [quests_reset_exclude.strip() for quests_reset_exclude in quests_reset_excludes_str.split(',')]
        
        # section [scanner]: scanner settings
        self.__cfg_db_host = self._config.get("scanner", "db_host", fallback="localhost")
        self.__cfg_db_port = self._config.getint("scanner", "db_port", fallback=3306)
        self.__cfg_db_name = self._config.get("scanner", "db_name", fallback=None)
        self.__cfg_db_user = self._config.get("scanner", "db_user", fallback=None)
        self.__cfg_db_password = self._config.get("scanner", "db_password", fallback=None)
        self.__cfg_scanner_rescan_trigger_cmd = self._config.get("scanner", "rescan_trigger_cmd", fallback="exit 0")
        
        # section [telegram]: telegram feature settings
        self.__tg_info_enable = self._config.getboolean("telegram", "tg_info_enable", fallback=False)
        if self.__tg_info_enable:
            #Just read and check all the other TG related parameter, if function is enabled
            log.info(f"TG info feature activated")
            self.__token = self._config.get("telegram", "tg_bot_token", fallback=None)
            tg_chat_id_str = self._config.get("telegram", "tg_chat_id", fallback=None)
            if self.__token is None or tg_chat_id_str is None:
                error_str = f"TG options not set fully set in config.ini: 'tg_bot_token':{self.__token} 'tg_chat_id':{tg_chat_id_str}"
                log.error(error_str)
                raise ValueError(error_str)
            #convert parameter into list and remove whitespaces
            self.__tg_chat_id_list = [chat_id.strip() for chat_id in tg_chat_id_str.split(',')]
            quest_timewindow_str = self._config.get("general", "quest_rescan_timewindow")
            status, timewindow_list = self._get_timewindow_from_string(quest_timewindow_str)
            if status is False:
                error_str = f"EventManager: Error while read parameter 'quest_rescan_timewindow' from config.ini. Please check value and pattern: quest_rescan_timewindow = ##-##"
                log.error(error_str)
                raise ValueError(error_str)
            self.__quest_timewindow_start_h = timewindow_list[0]
            self.__quest_timewindow_end_h = timewindow_list[1]
        
        # section [discord]: 
        self.__dc_info_enable = self._config.getboolean("discord", "dc_info_enable", fallback=False)
        if self.__dc_info_enable:
            log.info(f"EventManager: Discord info feature activated")
            dc_webhook_url_str = self._config.get("discord", "dc_webhook_url", fallback=None)
            if dc_webhook_url_str is None:
                error_str = f"EventManager: 'dc_webhook_url' not set in config.ini"
                log.error(error_str)
                raise ValueError(error_str)
            
            #convert parameter into list and remove whitespaces
            self.__dc_webhook_url_list = [webhook_url.strip() for webhook_url in dc_webhook_url_str.split(',')]
            self.__dc_webook_username = self._config.get("discord", "dc_webhook_username", fallback="PoGo Event Bot")
            self.__dc_webhook_embedTitle = self._config.get("discord", "dc_webhook_embedTitle", fallback="Event Quest notification")

    def _update_event_cache(self):
        try:
            log.debug(f"Eventcache: update .eventcache ...")
            filepath = self.__eventcache_path + ".eventcache"
            f = open(filepath, "w")
            eventcache_json = {}
            eventcache_json["last_update"] = f"{helper_time_now().strftime('%Y-%m-%d %H:%M:%S')}"
            eventcache_json["events"] = []
            event_list = []
            for event in self._all_events:
                event_list.append(event.get_dict())
            eventcache_json["events"].append({"all" : event_list})
            event_list = []
            for event in self._quest_events:
                event_list.append(event.get_dict())
            eventcache_json["events"].append({"quests" : event_list})
            
            json.dump(eventcache_json, f)
            log.debug(f"Eventcache: update {filepath}: {eventcache_json}")
            f.close()
        except Exception as e:
            log.error(f"Eventcache: error in update {filepath}")
            log.exception("Exception info:")

    def _get_timewindow_from_string(self, timewindow_str):
        try:
            timewindow_list = []
            timewindow_str_list = timewindow_str.split('-')
            if len(timewindow_str_list) == 2:
                timewindow_list.append(int(timewindow_str_list[0]))
                timewindow_list.append(int(timewindow_str_list[1]))
                return True, timewindow_list
            else:
                return False, timewindow_list
        except Exception as e:
            log.error("Error in _get_timewindow_from_string().")
            log.exception("Exception info:")
            return False, timewindow_list

    def _convert_time(self, time_string, local=True):
        if time_string is None:
            return None
        time = datetime.strptime(time_string, "%Y-%m-%d %H:%M")
        if not local:
            time = time + timedelta(hours=self.tz_offset)
        return time

    def _get_local_tg_rescan_msg(self):
        now = helper_time_now()
        first_rescan_time = now.replace(hour=self.__quest_timewindow_start_h, minute=0)
        latest_rescan_time = now.replace(hour=self.__quest_timewindow_end_h, minute=0)
        if now < first_rescan_time:     # quest changed before quest rescan timewindow
            rescan_str = self._local['tg_questrescan_before'][self.__language]
        elif now < latest_rescan_time:  # quest changed during quest rescan timewindow
            rescan_str = self._local['tg_questrescan_during'][self.__language]
        else:                           # quest changed after quest rescan timewindow
            rescan_str = self._local['tg_questrescan_after'][self.__language]
        return rescan_str

    def _send_tg_info_questreset(self, event_name, event_change_str):
        if self.__tg_info_enable:
            rescan_str = self._get_local_tg_rescan_msg()
            event_trigger = self._local[event_change_str][self.__language]
            info_msg = Template(self._local['tg_questreset_tmpl'][self.__language]).safe_substitute(event_trigger=event_trigger, event_name=event_name, rescan_str=rescan_str)
            for chat_id in self.__tg_chat_id_list:
                result = self._api.send_message(chat_id, info_msg)
                if result["ok"]:
                    log.info(f"send Telegram info message:{info_msg} result:{result}")
                else:
                    log.error(f"send Telegram info message failed with result:{result}")

    def _send_dc_info_questreset(self, event_name, event_change_str):
        if self.__dc_info_enable:
            embedUsername = self.__dc_webook_username
            data = {
                "content" : "",
                "username" : embedUsername
            }
            event_trigger = self._local[event_change_str][self.__language]
            embedDescription = Template(self._local['dc_questreset_tmpl'][self.__language]).safe_substitute(event_trigger=event_trigger, event_name=event_name)
            embedTitle = self._local["dc_webhook_embedTitle"][self.__language]
            data["embeds"] = [{
                "description" : embedDescription,
                "title" : embedTitle
            }]
            for url in self.__dc_webhook_url_list:
                try:
                    result = requests.post(url, json = data)
                    result.raise_for_status()
                except requests.exceptions.HTTPError as err:
                    log.error(f"unable to sent Discord info message to url:{url} result:{result.status_code}")
                else:
                    log.info(f"send Discord info message:{embedDescription} to url:{url} result:{result.status_code}")

    def _reset_pokemon(self, eventchange_datetime_UTC):
        if self.__reset_pokemon_strategy == "filtered":
            self._madconnector.reset_filtered_pokemon(eventchange_datetime_UTC)
        else:
            self._madconnector.reset_all_pokemon()

    def _check_pokemon_resets(self):
        log.info("check pokemon changing events")
        try:
            #get current time to check for event start and event end
            now = helper_time_now()

            # check, if one of the pokemon event is just started or ended
            for event in self._pokemon_events:
                # event start during last check?
                if event.check_event_start(self._last_pokemon_reset_check, now):
                    log.info(f'EventManager: event start detected for event {event.name} ({event.etype}) -> reset pokemon')
                    # remove pokemon from MAD DB, which are scanned before event start and needs to be rescanned, adapt time from local to UTC time
                    self._reset_pokemon(event.start - timedelta(hours=self.tz_offset))
                    break
                # event end during last check?
                if event.check_event_end(self._last_pokemon_reset_check, now):
                    log.info(f'EventManager: event end detected for event {event.name} ({event.etype}) -> reset pokemon')
                    # remove pokemon from MAD DB, which are scanned before event end and needs to be rescanned, adapt time from local to UTC time
                    self._reset_pokemon(event.end - timedelta(hours=self.tz_offset))
                    break
            self._last_pokemon_reset_check = now
        except Exception as e:
                    log.error("Error while checking Pokemon Resets.")
                    log.exception("Exception info:")

    def _check_quest_resets(self):
        log.info("check quest changing events")
        try:
            #get current time to check for event start and event end
            now = helper_time_now()

            # check, if one of the pokemon event is just started or ended
            for event in self._quest_events:
                # event starts during last check?
                if "start" in self.__quests_reset_types.get(event.etype, []):
                    if event.check_event_start(self._last_quest_reset_check, now):
                        log.info(f'EventManager: event start detected for event {event.name} ({event.etype}) -> reset quests')
                        # remove all quests from MAD DB
                        self._madconnector.reset_all_quests()
                        self._madconnector.trigger_rescan()
                        self._send_tg_info_questreset(event.name, "start")
                        self._send_dc_info_questreset(event.name, "start")
                        break
                # event end during last check?
                if "end" in self.__quests_reset_types.get(event.etype, []):
                    if event.check_event_end(self._last_quest_reset_check, now):
                        log.info(f'EventManager: event end detected for event {event.name} ({event.etype}) -> reset quests')
                        # remove all quests from MAD DB
                        self._madconnector.reset_all_quests()
                        self._madconnector.trigger_rescan()
                        self._send_tg_info_questreset(event.name, "end")
                        self._send_dc_info_questreset(event.name, "end")
                        break
            self._last_quest_reset_check = now
        except Exception as e:
            log.error("Error while checking Quest Resets.")
            log.exception("Exception info:")

    def _update_spawn_events_in_scanner(self):
        '''
        # abort, if there is no spawn event in list -> nothing to do
        if len(self._spawn_events) == 0:
            log.info("no spawnpoint changing events -> no event update in MAD-DB needed")
            return
        '''
        log.info("Check spawnpoint changing events")
        try:
            # read current event entries from scanner db
            db_events = self._madconnector.get_events()
            events_in_db = {}
            for db_event in db_events:
                events_in_db[db_event["event_name"]] = {
                    "event_start": db_event["event_start"],
                    "event_end": db_event["event_end"]
                }

            # check if there are missing event entries in the db and if so, create them
            for event_type_name in self.type_to_name.values():
                if event_type_name not in events_in_db.keys():
                    self._madconnector.insert_event(event_type_name)
                    events_in_db[event_type_name] = {
                        "event_start": DEFAULT_TIME,
                        "event_end": DEFAULT_TIME
                    }

            # go through all events that boost spawns, check if their times differ from the event in the db
            # and if so, update the db accordingly
            updated_mad_events = []
            for event in self._spawn_events:
                if event.etype not in updated_mad_events:
                    type_name = self.type_to_name.get(event.etype, "Others")
                    db_entry = events_in_db[type_name]
                    #handle unknown eventstart
                    if event.start is None:
                        continue
                    if db_entry["event_start"] != event.start or db_entry["event_end"] != event.end:
                        event_start = event.start.strftime('%Y-%m-%d %H:%M:%S')
                        event_end = event.end.strftime('%Y-%m-%d %H:%M:%S')
                        event_lure_duration = event.bonus_lure_duration if event.bonus_lure_duration is not None else DEFAULT_LURE_DURATION
                        event_name = self.type_to_name.get(event.etype, "Others")
                        self._madconnector.update_event(event_name, event_start, event_end, event_lure_duration)

                    updated_mad_events.append(event.etype)

            # just deletes all events that aren't part of EventManager
            if self.__delete_events:
                for db_event_name in events_in_db:
                    if not db_event_name in self.type_to_name.values():
                        self._madconnector.delete_event(db_event_name)

        except Exception as e:
            log.error("Error while checking Spawn Events.")
            log.exception("Exception info:")

    def _get_events(self):
        log.info("Update event list from external")
        try:
            # get the event list from github
            pogo_info_event_list = PogoInfoEventList()
            raw_events = pogo_info_event_list.get_json()
            self._all_events = []
            self._spawn_events = []
            self._quest_events = []
            self._pokemon_events = []

            # sort out events that have ended, bring them into a format that's easier to work with
            # and put them into seperate lists depending if they boost spawns or reset quests
            # then sort those after their start time
            for raw_event in raw_events:
                log.debug(f"_get_events: handling new raw_event:{raw_event}")
                new_event = PoGoEvent.fromPogoinfo(raw_event)
                # sort out invalid or outdated events
                if new_event is None:
                    continue
                if new_event.end < helper_time_now():
                    continue
                # store valid events
                self._all_events.append(new_event)
                # get events with changed spawnpoints
                # TBD: check how to handle events with just bonus_lure_duration. Hint: MAD ignores lure_duration setting for event 'DEFAULT' (see function _extract_args_single_stop)
                if new_event.has_spawnpoints:
                    self._spawn_events.append(new_event)
                # get events with changed quests
                if new_event.has_quests:
                    exclude_event = False
                    if self.__quests_reset_excludes_list is not None:
                        #exclude events according exclude strings from configuration
                        for quests_reset_excludes in self.__quests_reset_excludes_list:
                            if new_event.name.lower().find(quests_reset_excludes.lower()) != -1:
                                log.info(f"skipped quest event {new_event.name}, because matching exclude string '{quests_reset_excludes}'")
                                exclude_event = True
                                break
                    if not exclude_event:
                        self._quest_events.append(new_event)
                # get events which has changed pokemon pool
                if new_event.has_pokemon:
                    self._pokemon_events.append(new_event)

            #sort pokemon lists
            self._quest_events = sorted(self._quest_events, key=lambda e: (e.start is None, e.start))
            self._spawn_events = sorted(self._spawn_events, key=lambda e: (e.start is None, e.start))
            self._pokemon_events = sorted(self._pokemon_events, key=lambda e: (e.start is None, e.start))
            self._all_events = sorted(self._all_events, key=lambda e: (e.start is None, e.start))
            self._update_event_cache()
        except Exception as e:
            log.error("Error while getting events.")
            log.exception("Exception info:")

    def connect(self):
        self._madconnector = MadConnector(self.__cfg_db_host, self.__cfg_db_port, self.__cfg_db_name, self.__cfg_db_user, self.__cfg_db_password, self.__cfg_scanner_rescan_trigger_cmd)
        if(self.__tg_info_enable):
            self._api = SimpleTelegramApi(self.__token)
        #@todo: discord 

        # load events initally and update scanner event DB entries
        self._get_events()
        self._update_spawn_events_in_scanner()
        self._last_event_update = helper_time_now()

    def run(self):
        #if enabled, run pokemon reset check every cycle to ensure pokemon rescan just after spawn event change
        if self.__reset_pokemon_enable:
            self._check_pokemon_resets()

        #if enabled, run quest reset check every cycle to ensure quest rescan just after quest event change
        if self.__reset_quests_enable:
            self._check_quest_resets()

        # check for new events on event website only with configurated event check time
        # check after reset actions to avoid removing events before event end is detected.
        if (helper_time_now() - self._last_event_update) >= timedelta(seconds=self.__sleep):
            self._get_events()
            self._update_spawn_events_in_scanner()
            self._last_event_update = helper_time_now()

        # wait mainloop time
        log.info(f"sleep {self.__sleep_mainloop_in_s} seconds...")
        time.sleep(self.__sleep_mainloop_in_s)

'''
****************************************
* Module functions
****************************************
'''
def helper_time_now():
    return datetime.now()
