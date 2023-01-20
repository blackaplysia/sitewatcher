#!/usr/bin/python3

from sitewatcher.interfaces.ifprinter import BasePrinter

class Printer(BasePrinter):

    def __init__(self, args=None, variables=None):
        pass

    def print(self, site_name, site_link, message, text, link, hash=None):
        if hash is None:
            print(' '.join([site_name, message]))
        else:
            print(' '.join([hash, site_name, message]))
