#!/usr/local/bin/python
# -*- coding: utf-8 -*-

'''
Links:
- https://realpython.com/python-mock-library/#what-is-mocking
- 
'''

'''
****************************************
* Import
****************************************
'''
# unit testing
import unittest
from unittest.mock import patch, MagicMock
# logging
import logging
from logging.handlers import RotatingFileHandler
# time handling
import time
from datetime import datetime, timedelta

#test objects
import eventmanager
import mysql.connector
import requests

'''
****************************************
* Constants
****************************************
'''
#testdata
TESTDATA_SPAWNS_DUMMYPOKEMON = [{"id": 123,"template": "POKEMONNAME"}]
TESTDATA_DEFAULT_START_TIME = datetime(2010, 1, 1, hour=10, minute=0)
TESTDATA_DEFAULT_END_TIME = datetime(2010, 1, 1, hour=12, minute=0)
TESTDATA_DEFAULT_NOW_TIME = datetime(2010, 1, 1, hour=9, minute=59)
TESTDATA_DEFAULT_EVENTNAME = "TestEvent"

# test event data
TESTEVENT_POKEMON_BY_TYPE_1 = {'name': TESTDATA_DEFAULT_EVENTNAME, 'type': "", 'start': TESTDATA_DEFAULT_START_TIME.strftime("%Y-%m-%d %H:%M"), 'end': TESTDATA_DEFAULT_END_TIME.strftime("%Y-%m-%d %H:%M"), 'has_spawnpoints': False, 'has_quests': False, 'bonuses': [], 'bonus_lure_duration': None, 'spawns': []}

'''
****************************************
* Global variables
****************************************
'''
#logging
log = logging.getLogger() # root logger

'''
****************************************
* Classes
****************************************
'''
class TestEventManager(unittest.TestCase):
    def setUp(self):
        log_teststep(0, "setUp")
        """setup mocks, which is applied to each test in this TestCase"""
        # mock telegram send_message to always return ok (used to avoid flooding Telegram API, which will lead to exceed telegrm limits)
        patcher = patch('eventmanager.SimpleTelegramApi.send_message', autospec=True)
        self.mock_tg_send = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_tg_send.return_value = {"ok": True}
        
        # mock request.post function, used by discord send (used to avoid flooding Discord API)
        patcher = patch('requests.post', autospec=True)
        self.mock_requests_post = patcher.start()
        self.addCleanup(patcher.stop)
        self.request_response = requests.Response()
        self.request_response.status_code = 200
        self.mock_requests_post.return_value = self.request_response
        
        # mock time.sleep, otherwise tests tooks too long...
        patcher = patch('time.sleep', autospec=True)
        self.mock_sleep = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_sleep.return_value = None
        
        # mock helper_time_now to simulate different datetime.now()
        patcher = patch('eventmanager.helper_time_now', autospec=True)
        self.mock_now = patcher.start()
        self.addCleanup(patcher.stop)
        
        # mock MadConnector so no real scanner and database is needed
        patcher = patch('eventmanager.MadConnector.get_events', autospec=True)
        self.mock_mad_get_events = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('eventmanager.MadConnector.insert_event', autospec=True)
        self.mock_mad_insert_event = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('eventmanager.MadConnector.update_event', autospec=True)
        self.mock_mad_update_event = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('eventmanager.MadConnector.delete_event', autospec=True)
        self.mock_mad_delete_event = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('eventmanager.MadConnector.reset_all_quests', autospec=True)
        self.mock_mad_reset_all_quests = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('eventmanager.MadConnector.reset_all_pokemon', autospec=True)
        self.mock_mad_reset_all_pokemon = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('eventmanager.MadConnector.reset_filtered_pokemon', autospec=True)
        self.mock_mad_reset_filtered_pokemon = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('eventmanager.MadConnector.trigger_rescan', autospec=True)
        self.mock_mad_trigger_rescan = patcher.start()
        self.addCleanup(patcher.stop)

    @patch('eventmanager.PogoInfoEventList.get_json')
    def test_get_events_pokemon_event_by_spawns(self, mock_get_json):
        testevent1 = helper_generate_raw_eventdata(
            event_type = "event",
            event_name="testevent",
            start = TESTDATA_DEFAULT_START_TIME,
            end = TESTDATA_DEFAULT_END_TIME,
            has_spawnpoints=False,
            has_quests=False,
            spawns=TESTDATA_SPAWNS_DUMMYPOKEMON)
        raw_event_list = [testevent1]
        testhelper_get_events(self, mock_get_json, raw_event_list, num_all=1, num_pokemon=1, num_quest=0, num_spawn=0)

    @patch('eventmanager.PogoInfoEventList.get_json')
    def test_get_events_pokemon_event_by_type_1(self, mock_get_json):
        testevent1 = helper_generate_raw_eventdata(
            event_type = "community-day",
            event_name="testevent",
            start = TESTDATA_DEFAULT_START_TIME,
            end = TESTDATA_DEFAULT_END_TIME,
            has_spawnpoints=False,
            has_quests=False)
        raw_event_list = [testevent1]
        testhelper_get_events(self, mock_get_json, raw_event_list, num_all=1, num_pokemon=1, num_quest=0, num_spawn=0)

    @patch('eventmanager.PogoInfoEventList.get_json')
    def test_get_events_pokemon_event_by_type_2(self, mock_get_json):
        testevent1 = helper_generate_raw_eventdata(
            event_type = "spotlight-hour",
            event_name="testevent",
            start = TESTDATA_DEFAULT_START_TIME,
            end = TESTDATA_DEFAULT_END_TIME,
            has_spawnpoints=False,
            has_quests=False)
        raw_event_list = [testevent1]
        testhelper_get_events(self, mock_get_json, raw_event_list, num_all=1, num_pokemon=1, num_quest=0, num_spawn=0)

    @patch('eventmanager.PogoInfoEventList.get_json')
    def test_get_events_quest_event(self, mock_get_json):
        
        testevent1 = helper_generate_raw_eventdata(
            event_type = "event",
            event_name="testevent",
            start = TESTDATA_DEFAULT_START_TIME,
            end = TESTDATA_DEFAULT_END_TIME,
            has_spawnpoints=False,
            has_quests=True)
        raw_event_list = [testevent1]
        testhelper_get_events(self, mock_get_json, raw_event_list, num_all=1, num_pokemon=0, num_quest=1, num_spawn=0)

    @patch('eventmanager.PogoInfoEventList.get_json')
    def test_get_events_spawn_event(self, mock_get_json):
        testevent1 = helper_generate_raw_eventdata(
            event_type = "event",
            event_name="testevent",
            start = TESTDATA_DEFAULT_START_TIME,
            end = TESTDATA_DEFAULT_END_TIME,
            has_spawnpoints=True,
            has_quests=False)
        raw_event_list = [testevent1]
        testhelper_get_events(self, mock_get_json, raw_event_list, num_all=1, num_pokemon=0, num_quest=0, num_spawn=1)

    @patch('eventmanager.PogoInfoEventList.get_json')
    def test_quest_reset(self, mock_get_json):
        test_step = 1
        # mock PogoInfoEventList.get_json to provide test event
        start = datetime(2010, 1, 1, hour=10, minute=0)
        end = datetime(2010, 1, 1, hour=12, minute=0)
        testevent_1 = helper_generate_raw_eventdata(event_type = "event", event_name="testevent", start = start, end = end, has_spawnpoints=False, has_quests=True)
        mock_get_json.return_value = [testevent_1]
        log_teststep(0, "testevent with start:'2010-01-01 10:00', end:'2010-01-01 12:00'")
        
        self.mock_now.return_value = datetime(2010, 1, 1, hour=9, minute=59, second=59)
        self.assertTrue(helper_eventmanager_create_and_check(self, config_file_name = "/test/config_test.ini"))
        
        test_step = log_teststep(test_step, "event_manager.connect() t='2010-01-01 09:59:59'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=9, minute=59, second=59)
        self.assertTrue(helper_eventmanager_connect(self))
        testhelper_check_questevent_not_triggered(self)
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 09:59:59'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=9, minute=59, second=59)
        self._event_manager.run()
        testhelper_check_questevent_not_triggered(self)
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 10:00:00' -> event start triggered")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=10, minute=0, second=0)
        self._event_manager.run()
        testhelper_check_questevent_triggered(self)
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 10:00:01'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=10, minute=0, second=1)
        self._event_manager.run()
        testhelper_check_questevent_not_triggered(self)
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 11:59:59'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=11, minute=59, second=59)
        self._event_manager.run()
        testhelper_check_questevent_not_triggered(self)
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 12:00:00' -> event end triggered")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=12, minute=0, second=0)
        self._event_manager.run()
        testhelper_check_questevent_triggered(self)
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 12:00:01'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=12, minute=0, second=1)
        self._event_manager.run()
        testhelper_check_questevent_not_triggered(self)

    @patch('eventmanager.PogoInfoEventList.get_json')
    def test_pokemon_reset_filtered(self, mock_get_json):
        test_step = 1
        # mock PogoInfoEventList.get_json to provide test event
        start = datetime(2010, 1, 1, hour=10, minute=0)
        end = datetime(2010, 1, 1, hour=12, minute=0)
        testevent_1 = helper_generate_raw_eventdata(event_type = "event", event_name="testevent", start = start, end = end, has_spawnpoints=False, has_quests=False, spawns=TESTDATA_SPAWNS_DUMMYPOKEMON)
        mock_get_json.return_value = [testevent_1]
        log_teststep(0, "testevent with start:'2010-01-01 10:00', end:'2010-01-01 12:00'")
        
        self.mock_now.return_value = datetime(2010, 1, 1, hour=9, minute=59, second=59)
        self.assertTrue(helper_eventmanager_create_and_check(self, config_file_name = "/test/config_test.ini"))
        self._event_manager._EventManager__reset_pokemon_enable = True
        self._event_manager._EventManager__reset_pokemon_strategy = "filtered"
        
        test_step = log_teststep(test_step, "event_manager.connect() t='2010-01-01 09:59:59'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=9, minute=59, second=59)
        self.assertTrue(helper_eventmanager_connect(self))
        self.mock_mad_reset_filtered_pokemon.assert_not_called()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 09:59:59'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=9, minute=59, second=59)
        self._event_manager.run()
        self.mock_mad_reset_filtered_pokemon.assert_not_called()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 10:00:00' -> event start triggered")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=10, minute=0, second=0)
        self._event_manager.run()
        self.mock_mad_reset_filtered_pokemon.assert_called()
        self.mock_mad_reset_filtered_pokemon.reset_mock()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 10:00:01'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=10, minute=0, second=1)
        self._event_manager.run()
        self.mock_mad_reset_filtered_pokemon.assert_not_called()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 11:59:59'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=11, minute=59, second=59)
        self._event_manager.run()
        self.mock_mad_reset_filtered_pokemon.assert_not_called()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 12:00:00' -> event end triggered")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=12, minute=0, second=0)
        self._event_manager.run()
        self.mock_mad_reset_filtered_pokemon.assert_called()
        self.mock_mad_reset_filtered_pokemon.reset_mock()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 12:00:01'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=12, minute=0, second=1)
        self._event_manager.run()
        self.mock_mad_reset_filtered_pokemon.assert_not_called()

    @patch('eventmanager.PogoInfoEventList.get_json')
    def test_pokemon_reset_all(self, mock_get_json):
        test_step = 1
        # mock PogoInfoEventList.get_json to provide test event
        start = datetime(2010, 1, 1, hour=10, minute=0)
        end = datetime(2010, 1, 1, hour=12, minute=0)
        testevent_1 = helper_generate_raw_eventdata(event_type = "event", event_name="testevent", start = start, end = end, has_spawnpoints=False, has_quests=False, spawns=TESTDATA_SPAWNS_DUMMYPOKEMON)
        mock_get_json.return_value = [testevent_1]
        log_teststep(0, "testevent with start:'2010-01-01 10:00', end:'2010-01-01 12:00'")
        
        self.mock_now.return_value = datetime(2010, 1, 1, hour=9, minute=59, second=59)
        
        self.assertTrue(helper_eventmanager_create_and_check(self, config_file_name = "/test/config_test.ini"))
        self._event_manager._EventManager__reset_pokemon_enable = True
        self._event_manager._EventManager__reset_pokemon_strategy = "all"
        
        test_step = log_teststep(test_step, "event_manager.connect() t='2010-01-01 09:59:59'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=9, minute=59, second=59)
        self.assertTrue(helper_eventmanager_connect(self))
        self.mock_mad_reset_all_pokemon.assert_not_called()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 09:59:59'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=9, minute=59, second=59)
        self._event_manager.run()
        self.mock_mad_reset_all_pokemon.assert_not_called()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 10:00:00' -> event start triggered")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=10, minute=0, second=0)
        self._event_manager.run()
        self.mock_mad_reset_all_pokemon.assert_called()
        self.mock_mad_reset_all_pokemon.reset_mock()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 10:00:01'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=10, minute=0, second=1)
        self._event_manager.run()
        self.mock_mad_reset_all_pokemon.assert_not_called()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 11:59:59'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=11, minute=59, second=59)
        self._event_manager.run()
        self.mock_mad_reset_all_pokemon.assert_not_called()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 12:00:00' -> event end triggered")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=12, minute=0, second=0)
        self._event_manager.run()
        self.mock_mad_reset_all_pokemon.assert_called()
        self.mock_mad_reset_all_pokemon.reset_mock()
        
        test_step = log_teststep(test_step, "event_manager.run() t='2010-01-01 12:00:01'")
        self.mock_now.return_value = datetime(2010, 1, 1, hour=12, minute=0, second=1)
        self._event_manager.run()
        self.mock_mad_reset_all_pokemon.assert_not_called()


@unittest.skip("Remove this line for real testenvironment testing")
class TestEventManagerWithTestenvironment(unittest.TestCase):
    @patch('eventmanager.PogoInfoEventList.get_json')
    def test_event_start_full(self, mock_get_json):
        test_step = 1
        # mock PogoInfoEventList.get_json to provide test event with all possible changes (spawns, quests and pokemon)
        now = datetime.now()
        start = helper_roundup_datetime_minutes(now)
        end = start + timedelta(minutes=1)
        testevent_1 = helper_generate_raw_eventdata(event_type = "event", event_name="real_testevent", start = start, end = end, has_spawnpoints=True, has_quests=True, spawns=TESTDATA_SPAWNS_DUMMYPOKEMON)
        mock_get_json.return_value = [testevent_1]
        log_teststep(0, f"start test:{now} | testevent with start:{start}, end:{end}")
        
        self.assertTrue(helper_eventmanager_create_and_check(self, config_file_name = "/test/config_realtest.ini"))
        self._event_manager._EventManager__reset_pokemon_enable = True
        self._event_manager._EventManager__reset_pokemon_strategy = "all"
        
        test_step = log_teststep(test_step, f"event_manager.connect() t={datetime.now()}")
        self.assertTrue(helper_eventmanager_connect(self))
        
        test_step = log_teststep(test_step, f"event_manager.run() t={datetime.now()}")
        self._event_manager.run()
        
        test_step = log_teststep(test_step, f"event_manager.run() t={datetime.now()} -> event start triggered")
        self._event_manager.run()
        
        test_step = log_teststep(test_step, f"event_manager.run() t={datetime.now()} -> event end triggered")
        self._event_manager.run()
        
        test_step = log_teststep(test_step, f"done...")

'''
****************************************
* Helper-functions
****************************************
'''
def testhelper_get_events(testclass, mock_get_json, raw_event_list, num_all, num_pokemon, num_quest, num_spawn):
        # mock PogoInfoEventList.get_json to provide test event
        mock_get_json.return_value = raw_event_list
        
        testclass.mock_now.return_value = TESTDATA_DEFAULT_NOW_TIME
        testclass.assertTrue(helper_eventmanager_create_and_check(testclass, config_file_name = "/test/config_test.ini"))
        testclass.assertTrue(helper_eventmanager_connect(testclass))
        testclass.assertEqual(len(testclass._event_manager._all_events), num_all)
        testclass.assertEqual(len(testclass._event_manager._pokemon_events), num_pokemon)
        testclass.assertEqual(len(testclass._event_manager._quest_events), num_quest)
        testclass.assertEqual(len(testclass._event_manager._spawn_events), num_spawn)

def testhelper_check_questevent_triggered(testclass):
        testclass.mock_mad_reset_all_quests.assert_called()
        testclass.mock_mad_trigger_rescan.assert_called()
        testclass.mock_requests_post.assert_called()
        testclass.mock_tg_send.assert_called()
        testclass.mock_mad_reset_all_quests.reset_mock()
        testclass.mock_mad_trigger_rescan.reset_mock()
        testclass.mock_tg_send.reset_mock()
        testclass.mock_requests_post.reset_mock()

def testhelper_check_questevent_not_triggered(testclass):
        testclass.mock_mad_reset_all_quests.assert_not_called()
        testclass.mock_mad_trigger_rescan.assert_not_called()
        testclass.mock_requests_post.assert_not_called()
        testclass.mock_tg_send.assert_not_called()

def helper_eventmanager_create_and_check(testclass, config_file_name):
    try:
        testclass._event_manager = eventmanager.EventManager(config_file_name)
        return True
    except Exception:
        log.error("Test-error in helper_eventmanager_create_and_check()")
        log.exception("Exception info:")
        testclass._event_manager = None
        return False

def helper_eventmanager_connect(testclass):
    try:
        testclass._event_manager.connect()
        return True
    except Exception:
        log.error("Test-error in helper_eventmanager_connect()")
        log.exception("Exception info:")
        return False

def helper_roundup_datetime_minutes(datetime_org):
    datetime_tmp = datetime(year = datetime_org.year, month = datetime_org.month, day = datetime_org.day, hour = datetime_org.hour, minute = datetime_org.minute + 1)
    return datetime_tmp

def helper_generate_raw_eventdata_pokemon_by_spawns(event_name, start, end):
    return helper_generate_raw_eventdata(event_type="event", event_name=event_name, start=start, end=end, has_spawnpoints=False, has_quests=False, spawns = TESTDATA_SPAWNS_DUMMYPOKEMON)

def helper_generate_raw_eventdata_pokemon_by_type1(event_name, start, end):
    return helper_generate_raw_eventdata(event_type="community-day", event_name=event_name, start=start, end=end, has_spawnpoints=False, has_quests=False)

def helper_generate_raw_eventdata_pokemon_by_type2(event_name, start, end):
    return helper_generate_raw_eventdata(event_type="spotlight-hour", event_name=event_name, start=start, end=end, has_spawnpoints=False, has_quests=False)

def helper_generate_raw_eventdata_quest(event_name, start, end):
    return helper_generate_raw_eventdata(event_type="event", event_name=event_name, start=start, end=end, has_spawnpoints=False, has_quests=True)

def helper_generate_raw_eventdata_spawn(event_name, start, end):
    return helper_generate_raw_eventdata(event_type="event", event_name=event_name, start=start, end=end, has_spawnpoints=True, has_quests=False)

def helper_generate_raw_eventdata(event_type, event_name, start, end, has_spawnpoints, has_quests, bonus_lure_duration = None, spawns = [], bonuses = []):
    try:
        event_dict = {'name': event_name, 'type': event_type, 'start': start.strftime("%Y-%m-%d %H:%M"), 'end': end.strftime("%Y-%m-%d %H:%M"), 'has_spawnpoints': has_spawnpoints, 'has_quests': has_quests, 'bonuses': bonuses, 'bonus_lure_duration': bonus_lure_duration, 'spawns': spawns}
        return event_dict
    except Exception:
        log.error("Test-error in helper_generate_raw_eventdata()")
        log.exception("Exception info:")
        return None

def config_logging(logger, console_loglevel = logging.INFO):
    # console logging configuration
    formatter_console = logging.Formatter('[%(asctime)s] [%(name)12s] [%(levelname)7s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_loglevel)
    console_handler.setFormatter(formatter_console)
    logger.addHandler(console_handler)
    
    # set log level
    logger.setLevel(logging.DEBUG)

def log_teststep(teststep_number, log_str):
    
    if teststep_number == 0:
        teststep_id = "init"
    else:
        teststep_id = teststep_number
    log.info(f"TESTSTEP [{teststep_id}]: {log_str}")
    return teststep_number + 1


'''
****************************************
* main functions
****************************************
'''
if __name__ == "__main__":
    config_logging(log, console_loglevel = logging.DEBUG)
    unittest.main()
