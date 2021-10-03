#!/usr/bin/python3

import csv
import hashlib
import requests
from urllib.parse import urlparse

from interfaces.ifsource import BaseSource

class Source(BaseSource):

    def get_file(self, link):

        res = None
        try:
            res = requests.get(link)
        except requests.exceptions.RequestException as e:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            logger.warning('{}: failed to fetch {}'.format(self.name, link))
            logger.debug(e)
            return None
        except Exception as e:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            logger.warning('{}: failed to fetch {}'.format(self.name, link))
            logger.debug(e)
            return None

        if res.status_code >= 400:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            logger.warning('{}: failed to fetch {}. Status code={}'.format(self.name, link, res.status_code))
            return None

        enc = res.encoding if res.encoding != 'ISO-8859-1' else None
        text = res.content.decode(enc)

        return text

    def get_links(self, text):
        links = {}
        lines = csv.reader(text.splitlines())
        for line in lines:
            text_list = []
            link_list = []
            for column in line:
                url_object = urlparse(column)
                if len(url_object.scheme) > 0 and len(url_object.netloc) > 0:
                    link_list.append(column)
                else:
                    text_list.append(column)
            tag = '::'.join(text_list)
            for link in link_list:
                hash = hashlib.md5((self.resid + link + tag).encode()).hexdigest()
                links.update({hash: { 'site': self.resid, 'parent': self.resid, 'name': '', 'link': link, 'tag': tag }})
        return links

    def make_link_set(self, hash, link, depth, ignores):
        text = self.get_file(link)
        if text is None:
            return None
        else:
            return self.get_links(text)

