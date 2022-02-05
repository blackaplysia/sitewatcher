#!/usr/bin/python3

class BasePrinter:

    def __init__(self, args=None, variables=None):
        pass

    def print_all(self, targets, debug_mode=False):
        name = targets['name']
        for h, v in targets['hashes'].items():
            if debug_mode is True:
                self.print(name, v['message'], v['text'], v['link'], h)
            else:
                self.print(name, v['message'], v['text'], v['link'], None)

    def print(self, title, message, text, link, hash=None):
        pass
