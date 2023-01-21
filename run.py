#!/usr/local/bin/python
# -*- coding: utf-8 -*-

'''
****************************************
* Import
****************************************
'''
import argparse
import logging
from logging.handlers import RotatingFileHandler
import eventmanager

'''
****************************************
* Constants
****************************************
'''
VALID_LOGLEVEL = ["ERROR", "WARNING", "INFO", "DEBUG"]
VALID_LOGLEVEL_FILE = ["ERROR", "WARNING", "INFO", "DEBUG", "NONE"]

'''
****************************************
* Global variables
****************************************
'''
log = logging.getLogger() # root logger

'''
****************************************
* Classes
****************************************
'''

'''
****************************************
* Module functions
****************************************
'''
def config_logging(logger, console_loglevel = logging.INFO, file_loglevel = None):
    # console logging configuration
    formatter_console = logging.Formatter('[%(asctime)s] [%(name)12s] [%(levelname)7s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_loglevel)
    console_handler.setFormatter(formatter_console)
    logger.addHandler(console_handler)
    
    # file logging
    if file_loglevel is not None:
        formatter_file = logging.Formatter('[%(asctime)s] [%(name)12s] [%(levelname)7s] %(message)s')
        file_handler = RotatingFileHandler('eventmanager.log', maxBytes=10**5, backupCount=5)
        file_handler.setLevel(file_loglevel)
        file_handler.setFormatter(formatter_file)
        logger.addHandler(file_handler)
    
    logger.setLevel(logging.DEBUG)

def is_valid_loglevel(loglevel):
    return any(loglevel in sub for sub in VALID_LOGLEVEL)

'''
****************************************
* main functions
****************************************
'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-lc', '--log-level-console', default='INFO', choices=VALID_LOGLEVEL, required=False, help='set log level for console. Default:INFO')
    parser.add_argument('-lf', '--log-level-file', default='NONE', choices=VALID_LOGLEVEL_FILE, required=False, help='set log level for logfile. Default:NONE')
    args = parser.parse_args()
    file_loglevel = args.log_level_file
    console_loglevel = args.log_level_console
    if not is_valid_loglevel(console_loglevel): 
        console_loglevel = "INFO"
    if not is_valid_loglevel(file_loglevel): 
        file_loglevel = None
    config_logging(log, console_loglevel = console_loglevel, file_loglevel = file_loglevel)
    
    log.info(f"Start EventManager...")
    event_manager = eventmanager.EventManager()
    event_manager.connect()
    while(True):
        event_manager.run()
