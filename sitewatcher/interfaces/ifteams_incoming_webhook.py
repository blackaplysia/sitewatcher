#!/usr/bin/python3

import os
import requests
import sys

from sitewatcher.interfaces.ifprinter import BasePrinter

class Printer(BasePrinter):

    def __init__(self, args=None, variables=None):
        self.webhook = variables.get('teams_incoming_webhook')
        if self.webhook is None:
            self.webhook = os.environ.get('TEAMS_INCOMING_WEBHOOK')

    def print(self, title, message, hash=None):

        if self.webhook is None:
            print(f'No webhook registration for {title}', file=sys.stderr)
            return

        data = {
            'type': 'message',
            'attachments': [
                {
                    'contentType': 'application/vnd.microsoft.card.adaptive',
                    'contentUrl': None,
                    'content': {
                        '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json',
                        'type':'AdaptiveCard',
                        'version':'1.2',
                        'body': [
                            {
                                'type': 'TextBlock',
                                'text': f'{message}'
                            }
                        ]
                    }
                }
            ]
        }

        res = None
        try:
            res = requests.post(self.webhook, json=data)
        except Exception as e:
            print(f'Webhook {type(e).__name__}: failed to send message ({message[0:32]})', file=sys.stderr)
            print(e, file=sys.stderr)
            return

        if res is not None:
            if res.status_code >= 400:
                print(f'Webhook {res.status_code}', file=sys.stderr)
