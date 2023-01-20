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

        site_name = targets['name']
        site_link = targets['link']
        all_items = []
        items = []
        count = 0
        for h, v in targets['hashes'].items():
            message = v['message']
            text = v['text']
            link = v['link']
            items.append(f'- [{text}]({link})\r')
            count = count + 1
            if count > 10:
                all_items.append(items)
                items = []
                count = 0
        if len(items) > 0:
            all_items.append(items)


        for items in all_items:

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
                            'title': f'{site_name} {site_link}',
                            'sections': contents
                        }
                    }
                ]
            }

            if self.webhook is None:
                print(f'No webhook registration for {site_name}', file=sys.stderr)
                return

            res = None
            try:
                res = requests.post(self.webhook, json=data)
            except Exception as e:
                print(f'Webhook {type(e).__name__}: failed to send message ({message[0:32]})', file=sys.stderr)
                print(e, file=sys.stderr)

            if res is None:
                print(f'Webhook {site_name} None', file=sys.stderr)
            else:
                print(f'Webhook {site_name} {res.status_code}', file=sys.stderr)

