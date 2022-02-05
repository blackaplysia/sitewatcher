#!/usr/bin/python3

from sitewatcher.interfaces.ifprinter import BasePrinter

class Printer(BasePrinter):

    def __init__(self, args=None, variables=None):
        pass

    def print(self, title, message, text, link, hash=None):
        if hash is None:
            print(' '.join([title, message]))
        else:
            print(' '.join([hash, title, message]))
