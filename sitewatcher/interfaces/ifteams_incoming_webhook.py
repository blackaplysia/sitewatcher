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

    def print_all(self, targets, debug_mode=False):

        name = targets['name']
        items = []
        for h, v in targets['hashes'].items():
            message = v['message']
            text = v['text']
            link = v['link']
            items.append(f'- [{text}]({link})\r')

        contents = [
            {
                'text': ''.join(items)
            }
        ]

        data = {
            'type': 'message',
            'attachments': [
                {
                    'contentType': 'application/vnd.microsoft.teams.card.o365connector',
                    'content': {
                        '@type': 'MessageCard',
                        '@context': 'https://schema.org/extensions',
                        'sections': contents
                    }
                }
            ]
        }

        if self.webhook is None:
            print(f'No webhook registration for {name}', file=sys.stderr)
            return

        res = None
        try:
            res = requests.post(self.webhook, json=data)
        except Exception as e:
            print(f'Webhook {type(e).__name__}: failed to send message ({message[0:32]})', file=sys.stderr)
            print(e, file=sys.stderr)
            return

        if res is None:
            print(f'Webhook {name} None', file=sys.stderr)
        else:
            print(f'Webhook {name} {res.status_code}', file=sys.stderr)

