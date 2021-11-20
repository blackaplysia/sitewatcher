#!/usr/bin/python3

import feedparser
import hashlib

from sitewatcher.interfaces.ifsource import BaseSource

class Source(BaseSource):

    def make_link_set(self, hash, link, depth, ignores):
        feed = None
        try:
            feed = feedparser.parse(link)
        except Exception as e:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            logger.warning('{}: failed to fetch {}'.format(self.name, link))
            logger.debug(e)
            return None

        links = {}
        for e in feed['entries']:
            url = e['link']
            title = e['title']
            hash = hashlib.md5((self.resid + url + title).encode()).hexdigest()
            links.update({hash: { 'site': self.resid, 'parent': self.resid, 'name': title, 'link': url, 'tag': title }})
        return links

if __name__ == '__main__':
    import sys
    import pprint
    if len(sys.argv) > 1:
        links = {}
        for i in range(1, len(sys.argv)):
            links.update(Source('(name)', '(resid)', None).make_link_set('(hash)', sys.argv[i], 0, None))
        pprint.pprint(links)
