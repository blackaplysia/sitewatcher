#!/usr/bin/python3

from interfaces.IfPrinter import IfPrinter

class IfStdout(IfPrinter):

    def __init__(self):
        pass

    def print(self, title, message, channel=None, hash=None):
        if hash is None:
            print(' '.join([title, message]))
        else:
            print(' '.join([hash, title, message]))
