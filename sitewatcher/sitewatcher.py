#!/usr/bin/python3

import difflib
import filetype
import hashlib
import io
import json
import logging
import os
import re
import requests
import sys
import time
from bs4 import BeautifulSoup
from datetime import datetime
from importlib import import_module
from redis import Redis
from urllib.parse import urljoin

logger = None
debug_mode = False

redis = None

json_section_data = 'data'
json_section_config = 'config'
json_section_header = 'header'
json_section_updated = 'updated'
json_section_links = 'links'

redis_skey_index = 'index'
redis_skey_ignores = 'ignores'
redis_skey_hashes = 'hashes'
redis_skey_latests = 'latests'
redis_skey_variables = 'variables'

redis_lkey_updated = 'updated'
redis_lmax_updated = 10

redis_strkey_resid = 'resid'

redis_hkey_name = 'name'
redis_hkey_depth = 'depth'
redis_hkey_filetype = 'filetype'
redis_hkey_link = 'link'
redis_hkey_parent = 'parent'
redis_hkey_tag = 'tag'
redis_hkey_site = 'site'

def is_redis_empty():
    return redis.dbsize() == 0

def add_redis_name(name, resid):
    name_lower = name.lower()
    redis.set(name_lower, resid)
    redis.hset(resid, redis_hkey_name, name)
    redis.sadd(redis_skey_index, name_lower)

def delete_redis_name(name, resid):
    name_lower = name.lower()
    redis.srem(redis_skey_index, name_lower)
    redis.delete(name_lower)
    redis.delete(resid)

def rename_redis_name(old_name, new_name, resid):
    old_name_lower = old_name.lower()
    new_name_lower = new_name.lower()
    redis.rename(old_name_lower, new_name_lower)
    redis.hset(resid, redis_hkey_name, new_name)
    redis.sadd(redis_skey_index, new_name_lower)
    redis.srem(redis_skey_index, old_name_lower)

def get_redis_names():
    return redis.smembers(redis_skey_index)

def get_redis_resid(name):
    name_lower = name.lower()
    return redis.get(name_lower)

def add_redis_ignores(link):
    redis.sadd(redis_skey_ignores, link)

def remove_redis_ignores(link):
    redis.srem(redis_skey_ignores, link)

def get_redis_ignores():
    return redis.smembers(redis_skey_ignores)

def set_redis_value(resid, hkey, hvalue):
    redis.hset(resid, hkey, hvalue)

def get_redis_value(resid, hkey):
    return redis.hget(resid, hkey)

def delete_redis_value(resid, hkey):
    redis.hdel(resid, hkey)

def delete_redis_values(resid):
    redis.delete(resid)

def add_redis_list_value(resid, lkey, lvalue, max_length=0, auto_remove=False):
    k = resid + '+' + lkey
    redis.lpush(k, lvalue)
    if max_length > 0 and redis.llen(k) > max_length:
        removed_value = redis.rpop(k)
        if auto_remove == True:
            redis.delete(resid + '+' + removed_value)

def get_redis_list_value(resid, lkey, index):
    return redis.lindex(resid + '+' + lkey, index)

def get_redis_list_values(resid, lkey):
    return redis.lrange(resid + '+' + lkey, 0, -1)

def delete_redis_list(resid, lkey):
    redis.delete(resid + '+' + lkey)

def add_redis_smember(resid, skey, svalue):
    redis.sadd(resid + '+' + skey, svalue)
    # redis.sadd(skey, svalue)

def remove_redis_smember(resid, skey, svalue):
    redis.srem(resid + '+' + skey, svalue)

def flush_redis_smembers(resid, skey):
    redis.delete(resid + '+' + skey)

def get_redis_smembers(resid, skey):
    return redis.smembers(resid + '+' + skey)

def delete_redis_set(resid, skey):
    redis.delete(resid + '+' + skey)

def set_redis_variable(resid, var, value):
    redis.hset(resid + '+' + redis_skey_variables, var, value)

def get_redis_variable(resid, var, override=False):
    value = redis.hget(resid + '+' + redis_skey_variables, var)
    if value is None and override is True:
        value = redis.hget(redis_skey_variables, var)
    return value

def get_redis_variables(resid, override=False):
    variables = redis.hgetall(resid + '+' + redis_skey_variables)
    if override:
        global_variables = redis.hgetall(redis_skey_variables)
        global_variables.update(variables)
        variables = global_variables
    return variables

def delete_redis_variable(resid, var):
    redis.hdel(resid + '+' + redis_skey_variables, var)

def delete_redis_variables(resid):
    redis.delete(resid + '+' + redis_skey_variables)

def set_redis_global_variable(var, value):
    redis.hset(redis_skey_variables, var, value)

def get_redis_global_variable(var):
    return redis.hget(redis_skey_variables, var)

def get_redis_global_variables():
    return redis.hgetall(redis_skey_variables)

def delete_redis_global_variable(var):
    redis.hdel(redis_skey_variables, var)

def delete_redis_global_variables():
    redis.delete(redis_skey_variables)

def dump_redis_data():
    index = redis.smembers(redis_skey_index)
    if index is None:
        return None

    global_config = {}
    ignores = redis.smembers(redis_skey_ignores)
    if ignores is not None:
        global_config.update({ redis_skey_ignores: list(ignores) })
    variables = redis.hgetall(redis_skey_variables)
    if variables is not None:
        global_config.update({ redis_skey_variables: variables })

    global_data = {}
    for n in index:
        resid = redis.get(n)
        name = redis.hget(resid, redis_hkey_name)
        link = redis.hget(resid, redis_hkey_link)
        depth = redis.hget(resid, redis_hkey_depth)
        filetype = redis.hget(resid, redis_hkey_filetype)
        if filetype is None:
            filetype = 'None'

        updated = []
        updated_date_list = redis.lrange(resid + '+' + redis_lkey_updated, 0, -1)
        for dt in updated_date_list:
            updated.append({ dt: list(redis.smembers(resid + '+' + dt))})

        config = {}
        ignores = redis.smembers(resid + '+' + redis_skey_ignores)
        if ignores is not None:
            config.update({ redis_skey_ignores: list(ignores) })
        variables = redis.hgetall(resid + '+' + redis_skey_variables)
        if variables is not None:
            config.update({ redis_skey_variables: variables })

        links = {}
        hashes = redis.smembers(resid + '+' + redis_skey_hashes)
        for h in hashes:
            hn = redis.hget(h, redis_hkey_name)
            hl = redis.hget(h, redis_hkey_link)
            hp = redis.hget(h, redis_hkey_parent)
            hs = redis.hget(h, redis_hkey_site)
            ht = redis.hget(h, redis_hkey_tag)
            links.update({
                h: {
                    redis_hkey_name: hn,
                    redis_hkey_link: hl,
                    redis_hkey_parent: hp,
                    redis_hkey_site: hs,
                    redis_hkey_tag: ht
                }
            })

        global_data.update({
            n: {
                json_section_header: {
                    redis_strkey_resid: resid,
                    redis_hkey_name: name,
                    redis_hkey_link: link,
                    redis_hkey_depth: depth,
                    redis_hkey_filetype: filetype,
                },
                json_section_config: config,
                json_section_updated: updated,
                json_section_links: links
            }
        })

        print('{}: {} links and {} sequences dumped'.format(name, len(hashes), len(updated_date_list)), file=sys.stderr)

    json = {
        json_section_config: global_config,
        json_section_data: global_data
    }

    return json

def load_redis_data(json):
    global_config = json[json_section_config]
    global_data = json[json_section_data]

    ignores = global_config[redis_skey_ignores]
    for i in ignores:
        redis.sadd(redis_skey_ignores, i)
    variables = global_config[redis_skey_variables]
    for k, v in variables.items():
        redis.hset(redis_skey_variables, k, v)

    for site in global_data:
        header = global_data[site][json_section_header]
        resid = header[redis_strkey_resid]

        name = header[redis_hkey_name]

        redis.set(site, resid)
        redis.hset(resid, redis_hkey_name, header[redis_hkey_name])
        redis.sadd(redis_skey_index, site)
        redis.hset(resid, redis_hkey_link, header[redis_hkey_link])
        redis.hset(resid, redis_hkey_depth, header[redis_hkey_depth])
        if header[redis_hkey_filetype] != 'None':
            redis.hset(resid, redis_hkey_filetype, header[redis_hkey_filetype])

        config = global_data[site][json_section_config]
        ignores = config[redis_skey_ignores]
        for i in ignores:
            redis.sadd(resid + '+' + redis_skey_ignores, i)
        variables = config[redis_skey_variables]
        for k, v in variables.items():
            redis.hset(resid + '+' + redis_skey_variables, k, v)

        updated = global_data[site][json_section_updated]
        for sequence in updated:
            dt = list(sequence)[0]
            redis.rpush(resid + '+' + redis_lkey_updated, dt)
            for uh in sequence[dt]:
                redis.sadd(resid + '+' + dt, uh)

        links = global_data[site][json_section_links]
        for h in links:
            redis.sadd(resid + '+' + redis_skey_hashes, h)
            redis.hset(h, redis_hkey_name, links[h][redis_hkey_name])
            redis.hset(h, redis_hkey_link, links[h][redis_hkey_link])
            if links[h][redis_hkey_parent] is not None:
                redis.hset(h, redis_hkey_parent, links[h][redis_hkey_parent])
            redis.hset(h, redis_hkey_site, links[h][redis_hkey_site])
            redis.hset(h, redis_hkey_tag, links[h][redis_hkey_tag])


        print('{}: {} links and {} sequences loaded'.format(name, len(links), len(updated)), file=sys.stderr)

    return len(global_data)

class Site:

    def __init__(self, name):
        self.name = name
        self.resid = get_redis_resid(self.name)
        if self.resid is None:
            self.resid = hashlib.md5(self.name.encode()).hexdigest()
            self.exists = False
        else:
            self.name = get_redis_value(self.resid, redis_hkey_name)
            self.exists = True

    def add(self, link, filetype, depth):
        if self.exists == True:
            print('already exists', file=sys.stderr)
            return False

        if link is None:
            print('invalid url', file=sys.stderr)
            return False

        if depth < 1:
            print('invalid depth', file=sys.stderr)
            return False

        add_redis_name(self.name, self.resid)
        set_redis_value(self.resid, redis_hkey_link, link)
        if filetype is not None:
            set_redis_value(self.resid, redis_hkey_filetype, filetype)
        set_redis_value(self.resid, redis_hkey_depth, depth)
        self.exists = True

        return True

    def delete(self):
        if self.exists == False:
            print('{}: no such a site'.format(self.name), file=sys.stderr)
            return False

        for updated in get_redis_list_values(self.resid, redis_lkey_updated):
            delete_redis_set(self.resid, updated)
        delete_redis_list(self.resid, redis_lkey_updated)

        hashes = get_redis_smembers(self.resid, redis_skey_hashes)
        for h in hashes:
            delete_redis_values(h)
        delete_redis_set(self.resid, redis_skey_hashes)
        delete_redis_set(self.resid, redis_skey_ignores)

        delete_redis_name(self.name, self.resid)
        self.exists = False
        return True

    def rename(self, new_name):
        if self.exists == False:
            print('{}: no such a site'.format(self.name), file=sys.stderr)
            return False

        old_name = self.name
        self.name = new_name
        rename_redis_name(old_name, self.name, self.resid)
        return True

    def config(self, linkv=None, filetypev=None, depthv=None, ignoresv=None, recognizev=None):
        if self.exists == False:
            print('{}: no such a site'.format(self.name), file=sys.stderr)
            return False

        if linkv is not None:
            set_redis_value(self.resid, redis_hkey_link, linkv[0])
        if filetypev is not None:
            if filetypev[0] != 'None':
                set_redis_value(self.resid, redis_hkey_filetype, filetypev[0].lower())
            else:
                delete_redis_value(self.resid, redis_hkey_filetype)
        if depthv is not None:
            set_redis_value(self.resid, redis_hkey_depth, depthv[0])
        if ignoresv is not None:
            for i in ignoresv:
                add_redis_smember(self.resid, redis_skey_ignores, i)
        if recognizev is not None:
            for r in recognizev:
                remove_redis_smember(self.resid, redis_skey_ignores, r)

        link = get_redis_value(self.resid, redis_hkey_link)
        filetype = get_redis_value(self.resid, redis_hkey_filetype)
        depth = get_redis_value(self.resid, redis_hkey_depth)
        ignores = get_redis_smembers(self.resid, redis_skey_ignores)
        if debug_mode is True:
            print('{} {} {} {} {}'.format(self.resid, self.name, link, filetype, depth))
            for i in ignores:
                print('{} {} ignores {}'.format(self.resid, self.name, i))
        else:
            print('{} {} {} {}'.format(self.name, link, filetype, depth))
            for i in ignores:
                print('{} ignores {}'.format(self.name, i))

        return True

    def set_variable(self, var, val):
        if self.exists == False:
            print('{}: no such a site'.format(self.name), file=sys.stderr)
            return False

        if val is not None:
            set_redis_variable(self.resid, var, val)
        else:
            delete_redis_variable(self.resid, var)

        if debug_mode is True:
            print('{} {} {} {}'.format(self.resid, self.name, var, val))
        else:
            print('{} {} {}'.format(self.name, var, val))

        return True

    def print_variables(self):
        if self.exists == False:
            print('{}: no such a site'.format(self.name), file=sys.stderr)
            return False

        variables = get_redis_variables(self.resid)
        for k, v in variables.items():
            if debug_mode is True:
                print('{} {} {} {}'.format(self.resid, self.name, k, v))
            else:
                print('{} {} {}'.format(self.name, k, v))

        return True

    def get_title(self, name, link, parent_name):
        title = name
        res = None
        try:
            res = requests.get(link)
        except requests.exceptions.InvalidSchema as e:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            logger.warning('{}: failed to fetch {}'.format(self.name, link))
            logger.debug(e)
            return title
        except requests.exceptions.RequestException as e:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            logger.warning('{}: failed to fetch {}'.format(self.name, link))
            logger.debug(e)
            return title
        except Exception as e:
            print('{}: failed to fetch {}'.format(self.name, link), file=sys.stderr)
            logger.warning('{}: failed to fetch {}'.format(self.name, link))
            logger.debug(e)
            return title

        if res is not None:
            if res.status_code >= 400:
                logger.warning('{}: failed to fetch {}. Status code={}'.format(self.name, link, res.status_code))
            else:
                ftype = filetype.guess(res.content)
                if ftype:
                    if parent_name is None:
                        parent_name = ''
                    title = '[' + ftype.extension + ']' + parent_name + '::' + title
                else:
                    real_title = None
                    enc = res.encoding if res.encoding != 'ISO-8859-1' else None
                    bs = BeautifulSoup(res.content, 'html.parser', from_encoding=enc)
                    bs_tag = bs.find('title')
                    bs_ogp = bs.find('meta', attrs={'property': 'og:title'})
                    if bs_ogp is not None:
                        real_title = bs_ogp.get('content')
                    elif bs_tag is not None:
                        real_title = bs_tag.get_text()
                    if real_title is not None:
                        real_title = real_title.strip()
                        lt = len(title)
                        lrt = len(real_title)
                        if lrt > 0:
                            if lt >= lrt and title.find(real_title) >= 0:
                                pass
                            elif lt <= lrt and real_title.find(title) >= 0:
                                title = real_title
                            else:
                                title = title + '::' + real_title.strip()

        return title

    def update(self, now=None):
        if self.exists == False:
            print('{}: no such a site'.format(self.name), file=sys.stderr)
            return False

        if now is None:
            now = time.time()

        link = get_redis_value(self.resid, redis_hkey_link)
        filetype = get_redis_value(self.resid, redis_hkey_filetype)
        depth = int(get_redis_value(self.resid, redis_hkey_depth))
        old_hashes = list(get_redis_smembers(self.resid, redis_skey_hashes))
        if len(old_hashes) == 0:
            logger.info('{}: first update'.format(self.name))
        ignores = get_redis_smembers(self.resid, redis_skey_ignores)
        ignores_all = get_redis_ignores()
        if ignores_all is not None:
            if ignores is None:
                ignores = ignores_all
            else:
                ignores.update(ignores_all)

        interface = filetype if filetype is not None else 'html' 
        module = import_module('.if' + interface, f'{__package__}.interfaces')
        source = module.Source(self.name, self.resid, logger)
        links = source.make_link_set(self.resid, link, depth, ignores)

        if links is None or len(links) == 0:
            logger.warning('{}: no links found'.format(self.name))
        else:
            hashes = links.keys()

            latests = list(set(hashes) - set(old_hashes))
            obsoletes = list(set(old_hashes) - set(hashes))

            logger.debug('{}: old: {}'.format(self.name, old_hashes))
            logger.debug('{}: new: {}'.format(self.name, hashes))
            logger.debug('{}: latests: {}'.format(self.name, latests))
            logger.debug('{}: obsoletes: {}'.format(self.name, obsoletes))

            if len(latests) > 0:
                for h in latests:
                    parent_name = None
                    parent = links[h]['parent']
                    if parent is not None:
                        if parent not in links:
                            parent_name = self.name
                        else:
                            parent_name = links[parent]['name']
                    title = self.get_title(links[h]['name'], links[h]['link'], parent_name)
                    if len(title) > 0:
                        links[h]['name'] = title
                        links[h]['tag'] = title + ' ---- ' + links[h]['link']
                    add_redis_smember(self.resid, redis_skey_hashes, h)
                    set_redis_value(h, redis_hkey_site, links[h]['site'])
                    set_redis_value(h, redis_hkey_name, links[h]['name'])
                    set_redis_value(h, redis_hkey_link, links[h]['link'])
                    if links[h]['parent'] is not None:
                        set_redis_value(h, redis_hkey_parent, links[h]['parent'])
                    set_redis_value(h, redis_hkey_tag, links[h]['tag'])
                    logger.info('{}: added: {} {}'.format(self.name, h, links[h]['tag']))

                if len(old_hashes) > 0:
                    for h in latests:
                        add_redis_smember(self.resid, str(now), h)

                print('{}: updated'.format(self.name), file=sys.stderr)

            for h in obsoletes:
                remove_redis_smember(self.resid, redis_skey_hashes, h)
                obsolete_tag = get_redis_value(h, redis_hkey_tag)
                delete_redis_value(h, redis_hkey_site)
                delete_redis_value(h, redis_hkey_name)
                delete_redis_value(h, redis_hkey_link)
                delete_redis_value(h, redis_hkey_parent)
                delete_redis_value(h, redis_hkey_tag)
                logger.info('{}: removed: {} {}'.format(self.name, h, obsolete_tag))

        add_redis_list_value(self.resid, redis_lkey_updated, str(now), redis_lmax_updated, True)
        logger.info('{}: updated: {}'.format(self.name, now))

        return True

    def links(self, sequence):
        if self.exists == False:
            print('{}: no such a site'.format(self.name), file=sys.stderr)
            return False

        if sequence is None:
            hashes = list(get_redis_smembers(self.resid, redis_skey_hashes))
        else:
            updated = get_redis_list_value(self.resid, redis_lkey_updated, sequence)
            if updated is not None:
                hashes = list(get_redis_smembers(self.resid, updated))

        if hashes is not None:
            if debug_mode is True:
                print('{} hashes {}'.format(self.name, hashes))
            for h in hashes:
                n = get_redis_value(h,redis_hkey_name)
                l = get_redis_value(h, redis_hkey_link)
                t = get_redis_value(h, redis_hkey_tag)
                ph = get_redis_value(h, redis_hkey_parent)
                if ph is None:
                    pl = None
                else:
                    pl = get_redis_value(ph, redis_hkey_link)
                sh = get_redis_value(h, redis_hkey_site)
                if sh is None:
                    sl = None
                else:
                    sl = get_redis_value(sh, redis_hkey_link)
                if debug_mode:
                    print('{} {} {} {} {} {} {} {}'.format(self.name, sh, ph, h, sl, pl, l, n))
                else:
                    print('{} {} {} {} {}'.format(self.name, sl, pl, l, n))

        return True

    def sequences(self):
        if self.exists == False:
            print('{}: no such a site'.format(self.name), file=sys.stderr)
            return False

        for seq in range(0, redis_lmax_updated):
            updated = get_redis_list_value(self.resid, redis_lkey_updated, seq)
            if updated is not None:
                hashes = list(get_redis_smembers(self.resid, updated))
                if hashes is None:
                    population = 0
                else:
                    population = len(hashes)
                updated_isotimestamp = datetime.utcfromtimestamp(float(updated)).isoformat()
                print('{} {} {} {} {}'.format(self.name, seq, population, updated, updated_isotimestamp))

    def print(self, sequence, device=None):
        if self.exists == False:
            print('{}: no such a site'.format(self.name), file=sys.stderr)
            return False

        variables = get_redis_variables(self.resid, override=True)

        updated = get_redis_list_value(self.resid, redis_lkey_updated, sequence)

        module = None
        printer = None
        interface = 'stdout'
        args = None
        if device is not None:
            device_parsed = device.split(':', 1)
            if len(device_parsed) >= 1:
                interface = device_parsed[0]
                if len(device_parsed) > 1 and len(device_parsed[1]) > 0:
                    args = device_parsed[1]
        try:
            module = import_module('.if' + interface, f'{__package__}.interfaces')
        except ModuleNotFoundError as e:
            print('{}: {} is not a printer device'.format(self.name, interface), file=sys.stderr)
            return False
        printer = module.Printer(args, variables)

        if updated is not None:
            hashes = list(get_redis_smembers(self.resid, updated))
            if debug_mode is True:
                updated_isotimestamp = datetime.utcfromtimestamp(float(updated)).isoformat()
                print('{} updated {} {}'.format(self.name, updated, updated_isotimestamp), file=sys.stderr)
            if hashes is not None:
                if debug_mode is True:
                    print('hashes: {}'.format(hashes), file=sys.stderr)
                for h in hashes:
                    tag = get_redis_value(h, redis_hkey_tag)
                    if tag is None:
                        tag = 'obsolete'
                    if debug_mode is True:
                        printer.print(self.name, tag, h)
                    else:
                        printer.print(self.name, tag)

    @classmethod
    def global_config(cls, linkv, filetypev, depthv, ignoresv, recognizev):
        if linkv is not None or filetypev is not None or depthv is not None:
            print('cannot apply to all sites', file=sys.stderr)
            return

        if ignoresv is not None:
            for i in ignoresv:
                add_redis_ignores(i)
        if recognizev is not None:
            for r in recognizev:
                remove_redis_ignores(r)

        for i in get_redis_ignores():
            print('global ignores {}'.format(i))

    @classmethod
    def global_set_variable(cls, var, val):
        if val is not None:
            set_redis_global_variable(var, val)
        else:
            delete_redis_global_variable(var)

        print('global {} {}'.format(var, val))

    @classmethod
    def global_print_variable(cls):
        variables = get_redis_global_variables()
        for k, v in variables.items():
            print('global {} {}'.format(k, v))

    @classmethod
    def export_data(cls):
        data = dump_redis_data()
        if data is None:
            print('no data to export', file=sys.stderr)
        else:
            print(json.dumps(data, ensure_ascii=False, indent=1))

    @classmethod
    def import_data(cls):
        if is_redis_empty() == False:
            print('database is not empty', file=sys.stderr)
        else:
            data = json.loads(sys.stdin.read())
            if data is None:
                print('no data to import', file=sys.stderr)
            else:
                count = load_redis_data(data)
                print('{} sites imported'.format(count), file=sys.stderr)

class SiteList:

    def __init__(self, name_template=None):
        self.site_name_list = None
        self.global_op = False
        if name_template is None:
            self.site_name_list = sorted(list(get_redis_names()))
        else:
            name_template_lower = name_template.lower()
            if name_template_lower == 'all':
                self.site_name_list = sorted(list(get_redis_names()))
            elif name_template_lower == 'global':
                self.global_op = True
            else:
                all_name_list = sorted(list(get_redis_names()))
                name_list = []
                for s in all_name_list:
                    if name_template_lower in s:
                        name_list.append(s)
                self.site_name_list = name_list

    def list(self):
        for s in self.site_name_list:
            resid = get_redis_resid(s)
            name = get_redis_value(resid, redis_hkey_name)
            link = get_redis_value(resid, redis_hkey_link)
            filetype = get_redis_value(resid, redis_hkey_filetype)
            depth = get_redis_value(resid, redis_hkey_depth)
            if debug_mode is True:
                print('{} {} {} {} {}'.format(resid, name, link, filetype, depth))
            else:
                print('{} {} {} {}'.format(name, link, filetype, depth))

    def config(self, linkv=None, filetypev=None, depthv=None, ignoresv=None, recognizev=None):
        if self.global_op == True:
            Site.global_config(args.link, args.filetype, args.depth, args.ignores, args.remove_ignores)
        else:
            for s in self.site_name_list:
                resid = get_redis_resid(s)
                name = get_redis_value(resid, redis_hkey_name)
                Site(name).config(linkv, filetypev, depthv, ignoresv, recognizev)

    def set_variable(self, var, val):
        if self.global_op == True:
            Site.global_set_variable(var, val)
        else:
            for s in self.site_name_list:
                resid = get_redis_resid(s)
                name = get_redis_value(resid, redis_hkey_name)
                Site(name).set_variable(var, val)

    def print_variables(self):
        if self.global_op == True:
            Site.global_print_variable()
        else:
            for s in self.site_name_list:
                resid = get_redis_resid(s)
                name = get_redis_value(resid, redis_hkey_name)
                Site(name).print_variables()

    def update(self):
        now = time.time()
        for s in self.site_name_list:
            resid = get_redis_resid(s)
            name = get_redis_value(resid, redis_hkey_name)
            Site(name).update(now)

    def print(self, sequence, device):
        for s in self.site_name_list:
            resid = get_redis_resid(s)
            name = get_redis_value(resid, redis_hkey_name)
            Site(name).print(sequence,device)

    def links(self, sequence):
        for s in self.site_name_list:
            resid = get_redis_resid(s)
            name = get_redis_value(resid, redis_hkey_name)
            Site(name).links(sequence)

    def sequences(self):
        for s in self.site_name_list:
            resid = get_redis_resid(s)
            name = get_redis_value(resid, redis_hkey_name)
            Site(name).sequences()

def main():

    global redis
    global logger
    global debug_mode

    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = os.environ.get('REDIS_PORT', '6379')
    logs_dir = os.environ.get('LOGS_DIR', '.')

    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    import argparse
    import csv
    from argparse import HelpFormatter
    from operator import attrgetter
    class SortingHelpFormatter(HelpFormatter):
        def add_arguments(self, actions):
            actions = sorted(actions, key=attrgetter('option_strings'))
            super(SortingHelpFormatter, self).add_arguments(actions)

    parser = argparse.ArgumentParser(description='Check updating of web sites', formatter_class=SortingHelpFormatter)
    parser.add_argument('--debug', action='store_true', help='debug output')
    parser.add_argument('--timestamp', action='store_true', help='print timestamp to /dev/stderr')

    sps = parser.add_subparsers(dest='subparser_name', title='action arguments')
    sp_add = sps.add_parser('add', help='add a site')
    sp_add.add_argument('name', nargs=1, metavar='NAME', help='site name')
    sp_add.add_argument('link', nargs=1, metavar='URL', help='site url')
    sp_add.add_argument('--filetype', '-f', default=None, metavar='FILETYPE', help='file type')
    sp_add.add_argument('--depth', '-d', default='1', metavar='N', help='depth')
    sp_delete = sps.add_parser('delete', help='delete a site')
    sp_delete.add_argument('name', nargs=1, metavar='NAME', help='site name')
    sp_rename = sps.add_parser('rename', help='rename a site')
    sp_rename.add_argument('name', nargs=1, metavar='NAME', help='site name')
    sp_rename.add_argument('new_name', nargs=1, metavar='NEW_NAME', help='new name')
    sp_config = sps.add_parser('config', help='configure a site')
    sp_config.add_argument('name', nargs='?', metavar='NAME', help='site name')
    sp_config.add_argument('--link', '-l', nargs=1, metavar='URL', help='link')
    sp_config.add_argument('--filetype', '-f', nargs=1, metavar='(CSV)', help='file type (None to remove)')
    sp_config.add_argument('--depth', '-d', nargs=1, metavar='N', help='depth')
    sp_config.add_argument('--ignores', '-i', action='append', metavar='URL', help='add to ignore list')
    sp_config.add_argument('--remove-ignores', '-r', action='append', metavar='URL', help='remove from ignore list')
    sp_set = sps.add_parser('set', help='set a variable')
    sp_set.add_argument('name', nargs=1, metavar='NAME', help='site name')
    sp_set.add_argument('var', nargs=1, metavar='VAR', help='variable')
    sp_set.add_argument('value', nargs=1, metavar='VALUE', help='value')
    sp_unset = sps.add_parser('unset', help='unset a variable')
    sp_unset.add_argument('name', nargs=1, metavar='NAME', help='site name')
    sp_unset.add_argument('var', nargs=1, metavar='VAR', help='variable')
    sp_variables = sps.add_parser('variables', help='print variables')
    sp_variables.add_argument('name', nargs=1, metavar='NAME', help='site name')
    sp_update = sps.add_parser('update', help='update a site or all sites')
    sp_update.add_argument('name', nargs=1, metavar='NAME', help='site name (\'all\' for all sites)')
    sp_links = sps.add_parser('links', help='print all links of a site or all sites')
    sp_links.add_argument('name', nargs=1, metavar='NAME', help='site name (\'all\' for all sites)')
    sp_links.add_argument('--sequence', '-s', default=None, metavar='N', help='time sequence number (0-9, latest=0, all by default)')
    sp_print = sps.add_parser('print', help='print latest links of a site or all sites')
    sp_print.add_argument('name', nargs=1, metavar='NAME', help='site name (\'all\' for all sites)')
    sp_print.add_argument('--sequence', '-s', default='0', metavar='N', help='time sequence number (0-9, latest=0 by deafult)')
    sp_print.add_argument('--device', '-d', nargs=1, metavar='DEVICE', help='device information like DEVICE:ARGUMENT')
    sp_sequences = sps.add_parser('sequences', help='list time sequences')
    sp_sequences.add_argument('name', nargs=1, metavar='NAME', help='site name')
    sp_list = sps.add_parser('list', help='list sites')
    sp_list.add_argument('name', nargs='?', metavar='NAME', help='site name')
    sp_export = sps.add_parser('export', help='export database')
    sp_import = sps.add_parser('import', help='import database')

    if len(sys.argv) == 1:
        print(parser.format_usage(), file=sys.stderr)
        return 1

    args = parser.parse_args()

    debug_mode = args.debug

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(os.path.join(logs_dir, os.path.basename(__file__) + '.log'))
    if debug_mode:
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'))
        logger.addHandler(file_handler)

    method = args.subparser_name

    if args.timestamp:
        now_isotimestamp = datetime.utcfromtimestamp(time.time()).isoformat()
        print(f'# {method} {now_isotimestamp}', file=sys.stderr)

    redis = Redis(host=redis_host, port=redis_port, decode_responses=True)

    if method == 'add':
        Site(args.name[0]).add(args.link[0], args.filetype, int(args.depth))
    elif method == 'delete':
        Site(args.name[0]).delete()
    elif method == 'rename':
        Site(args.name[0]).rename(args.new_name[0])
    elif method == 'config':
        SiteList(args.name[0]).config(args.link, args.filetype, args.depth, args.ignores, args.remove_ignores)
    elif method == 'set':
        SiteList(args.name[0]).set_variable(args.var[0], args.value[0])
    elif method == 'unset':
        SiteList(args.name[0]).set_variable(args.var[0], None)
    elif method == 'variables':
        SiteList(args.name[0]).print_variables()
    elif method == 'update':
        SiteList(args.name[0]).update()
    elif method == 'links':
        SiteList(args.name[0]).links(args.sequence)
    elif method == 'print':
        device = None if args.device is None else args.device[0]
        SiteList(args.name[0]).print(args.sequence, device)
    elif method == 'sequences':
        SiteList(args.name[0]).sequences()
    elif method == 'list':
        SiteList(args.name).list()
    elif method == 'export':
        Site.export_data()
    elif method == 'import':
        Site.import_data()

    return 0

if __name__ == '__main__':
    exit(main())
