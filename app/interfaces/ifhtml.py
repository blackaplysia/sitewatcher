#!/usr/bin/python3

import hashlib
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from interfaces.ifsource import BaseSource

class Source(BaseSource):

    def get_references(self, bs, parent_hash, parent_link, links, ignores):
        children = {}
        for t in bs.find_all('a'):
            ref = t.get('href')
            if ref is not None:
                ref = ''.join(filter(lambda c: c >= ' ', ref))
                ref = re.sub('<.*?>', '', ref)
                ref = ref.strip()

                ref_lower = ref.lower()
                if ref_lower.startswith('#'):
                    pass
                elif ref_lower.startswith('mailto:'):
                    pass
                elif ref_lower.startswith('tel:'):
                    pass
                elif ref_lower.startswith('javascript:'):
                    pass
                else:
                    if parent_link is not None:
                        ref = urljoin(parent_link, ref)
                        ref_lower = ref.lower()
                    is_ignored = False
                    if ignores is not None:
                        for i in ignores:
                            if ref_lower.startswith(i):
                                is_ignored = True
                                break
                    if is_ignored is False:
                        cs = t.strings
                        if cs is not None:
                            title = re.sub('[　 ]+', ' ', '::'.join(filter(lambda x: len(x) > 0, [s.strip() for s in cs])))
                        tag = title + (' ' if len(title) > 0 else '') + '---- ' + ref
                        hash = hashlib.md5((self.resid + tag).encode()).hexdigest()
                        if hash not in links:
                            children.update({hash: { 'site': self.resid, 'parent': parent_hash, 'name': title, 'link': ref, 'tag': tag }})
        return children

    def make_link_set_recursive(self, hash, link, depth, links, ignores):

        res = None
        try:
            res = requests.get(link)
        except requests.exceptions.RequestException as e:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            self.logger.warning('{}: failed to fetch {}'.format(self.name, link))
            self.logger.debug(e)
            return None
        except Exception as e:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            self.logger.warning('{}: failed to fetch {}'.format(self.name, link))
            self.logger.debug(e)
            return None

        if res.status_code >= 400:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            self.logger.warning('{}: failed to fetch {}. Status code={}'.format(self.name, link, res.status_code))
            return None

        bs = BeautifulSoup(res.content, 'html.parser')
        children = self.get_references(bs, hash, link, links, ignores)
        links.update(children)

        if depth > 1:
            for h in children:
                descendant_links = self.make_link_set_recursive(h, children[h]['link'], depth - 1, links, ignores)
                if descendant_links is not None:
                    links.update(descendant_links)

        return links

    def make_link_set(self, hash, link, depth, ignores):
        return self.make_link_set_recursive(hash, link, depth, {}, ignores)
