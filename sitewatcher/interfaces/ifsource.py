#!/usr/bin/python3

class BaseSource:

    def __init__(self, name, resid, logger):
        self.name = name
        self.resid = resid
        self.logger = logger

    def make_link_set(self, hash, link, depth, ignores):
        return None

    def use_tag_title(self):
        return False
