#!/usr/bin/python3

class BasePrinter:

    def __init__(self, args=None, variables=None):
        pass

    def print_all(self, targets, debug_mode=False):
        site_name = targets['name']
        site_link = targets['link']
        for h, v in targets['hashes'].items():
            if debug_mode is True:
                self.print(site_name, site_link, v['message'], v['text'], v['link'], h)
            else:
                self.print(site_name, site_link, v['message'], v['text'], v['link'], None)

    def print(self, site_name, site_link, message, text, link, hash=None):
        pass
