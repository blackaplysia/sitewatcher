#!/usr/bin/python3

class PrintInterface:

    def __init__(self):
        pass

    def print(self, title, message, channel=None, hash=None):
        if hash is None:
            print(' '.join([title, message]))
        else:
            print(' '.join([hash, title, message]))
