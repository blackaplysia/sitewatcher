#!/usr/bin/python3

import os
import sys
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackClientError, SlackApiError

from interfaces.IfPrinter import IfPrinter

class IfSlack(IfPrinter):

    def __init__(self):
        token = os.environ.get('SLACK_BOT_TOKEN')
        self.client = WebClient(token=token)

    def print(self, title, message, channel, hash=None):
        try:
            self.client.chat_postMessage(channel=channel, text=' '.join([message]))
        except SlackApiError as e:
            if e.response.status_code == 429:
                delay = int(e.response.headers['Retry-After'])
                print('Rate limited. Retrying in {} seconds'.format(delay), file=sys.stderr)
                time.sleep(delay)
                self.client.chat_postMessage(channel=channel, text=' '.join([message]))
        except SlackClientError as e:
            print(e)
