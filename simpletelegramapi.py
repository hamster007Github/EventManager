#!/usr/local/bin/python
# -*- coding: utf-8 -*-

'''
****************************************
* Import
****************************************
'''
import json
# url handling
import urllib
import requests
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