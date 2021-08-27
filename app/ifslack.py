#!/usr/bin/python3

import os

from slack_sdk import WebClient
from ifprint import PrintInterface

class SlackInterface(PrintInterface):

    def __init__(self):
        token = os.environ.get("SLACK_BOT_TOKEN")
        self.client = WebClient(token=token)

    def print(self, title, message, channel, hash=None):
        self.client.chat_postMessage(channel=channel, text=' '.join([message]))
