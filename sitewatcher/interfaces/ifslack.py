#!/usr/bin/python3

import os
import sys
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackClientError, SlackApiError

from sitewatcher.interfaces.ifprinter import BasePrinter

class Printer(BasePrinter):

    def __init__(self, args=None, variables=None):
        token = variables.get('slack_bot_token')
        if token is None:
            token = os.environ.get('SLACK_BOT_TOKEN')
        self.client = WebClient(token=token)
        self.args = args
        self.variables = variables

    def print(self, title, message, hash=None):
        if self.args is not None:
            channel = '#' + self.args
        else:
            channel = self.variables.get('slack_channel')
            if channel is None:
                channel = '#general'

        try:
            self.client.chat_postMessage(channel=channel, text=' '.join([message]))
        except SlackApiError as e:
            if e.response.status_code == 429:
                delay = int(e.response.headers['Retry-After'])
                print('Rate limited. Retrying in {} seconds'.format(delay), file=sys.stderr)
                time.sleep(delay)
                self.client.chat_postMessage(channel=channel, text=' '.join([message]))
            elif e.response.status_code < 400:
                print('Slack api error: Status={}, Reason={}'.format(e.response.status_code, e.response['error']), file=sys.stderr)
        except SlackClientError as e:
            print(e)
