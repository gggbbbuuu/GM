# -*- coding: utf-8 -*-

"""
    BlackLodge Add-on
"""


from resources.lib.modules import control
from resources.lib.modules import cache
from resources.lib.modules import utils
from resources.lib.modules import log_utils
from resources.lib.modules import api_keys
from resources.lib.indexers import navigator

import os, sys

import requests

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

import six
from six.moves import urllib_parse


params = dict(urllib_parse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()

action = params.get('action')


class People:
    def __init__(self):
        self.list = []

        self.session = requests.Session()

        self.items_per_page = str(control.setting('items.per.page')) or '20'
        self.tm_user = control.setting('tm.user') or api_keys.tmdb_key

        self.personlist_link = 'https://api.themoviedb.org/3/person/popular?api_key=%s&language=en-US&page=1' % self.tm_user
        self.person_search_link = 'https://api.themoviedb.org/3/search/person?query=%s&api_key=%s&page=1' % ('%s', self.tm_user)
        self.person_movie_link = 'https://api.themoviedb.org/3/person/%s/movie_credits?api_key=%s' % ('%s', self.tm_user)
        self.person_tv_link = 'https://api.themoviedb.org/3/person/%s/tv_credits?api_key=%s' % ('%s', self.tm_user)
        self.bio_link = 'https://api.themoviedb.org/3/person/%s?api_key=%s' % ('%s', self.tm_user)
        self.tm_img_link = 'https://image.tmdb.org/t/p/w500%s'
        self.fallback_img = os.path.join(control.artPath(), 'person.png')


    def __del__(self):
        self.session.close()


    def persons(self, url=None, content=''):
        if not url:
            url = self.personlist_link
        #log_utils.log(url)
        self.list = cache.get(self.tmdb_person_list, 24, url)
        self.addDirectory(self.list, content)
        return self.list


    def search(self, content=''):
        navigator.navigator().addDirectoryItem(32603, 'peopleSearchnew&content=%s' % content, 'people-search.png', 'DefaultMovies.png')

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        try:
            dbcur.executescript("CREATE TABLE IF NOT EXISTS people (ID Integer PRIMARY KEY AUTOINCREMENT, term);")
        except:
            pass

        dbcur.execute("SELECT * FROM people ORDER BY ID DESC")
        lst = []

        delete_option = False
        for (id, term) in dbcur.fetchall():
            if term not in str(lst):
                delete_option = True
                navigator.navigator().addDirectoryItem(term.title(), 'peopleSearchterm&name=%s&content=%s' % (term, content), 'people-search.png', 'DefaultMovies.png', context=(32644, 'peopleDeleteterm&name=%s' % term))
                lst += [(term)]
        dbcur.close()

        if delete_option:
            navigator.navigator().addDirectoryItem(32605, 'clearCacheSearch&select=people', 'tools.png', 'DefaultAddonProgram.png')

        navigator.navigator().endDirectory(False)


    def search_new(self, content):
        control.idle()

        t = control.lang(32010)
        k = control.keyboard('', t)
        k.doModal()
        q = k.getText() if k.isConfirmed() else None

        if not q: return
        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM people WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO people VALUES (?,?)", (None,q))
        dbcon.commit()
        dbcur.close()
        url = self.person_search_link % urllib_parse.quote_plus(q)
        self.persons(url, content=content)


    def search_term(self, q, content):
        control.idle()
        q = q.lower()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM people WHERE term = ?", (q,))
        dbcur.execute("INSERT INTO people VALUES (?,?)", (None, q))
        dbcon.commit()
        dbcur.close()
        url = self.person_search_link % urllib_parse.quote_plus(q)
        self.persons(url, content=content)


    def delete_term(self, q):
        control.idle()

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()
        dbcur.execute("DELETE FROM people WHERE term = ?", (q,))
        dbcon.commit()
        dbcur.close()
        control.refresh()


    def bio_txt(self, id, name):
        try:
            url = self.bio_link % id
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            r.encoding = 'utf-8'
            r = r.json() if six.PY3 else utils.json_loads_as_str(r.text)
            txt = '[B]Born:[/B] {0}[CR]{1}[CR]{2}'.format(r['birthday'] or 'N/A', '[B]Died:[/B] {}[CR]'.format(r['deathday']) if r['deathday'] else '', r['biography'] or '[B]Biography:[/B] N/A')
            control.textViewer(text=txt, heading=name, monofont=False)
        except:
            log_utils.log('bio_txt', 1)
            return


    def tmdb_person_list(self, url):
        result = self.session.get(url, timeout=10)
        result.raise_for_status()
        result.encoding = 'utf-8'
        result = result.json() if six.PY3 else utils.json_loads_as_str(result.text)
        items = result['results']
        #log_utils.log(repr(items))

        try:
            page = int(result['page'])
            total = int(result['total_pages'])
            if page >= total: raise Exception()
            if 'page=' not in url: raise Exception()
            next = '%s&page=%s' % (url.split('&page=', 1)[0], page+1)
        except:
            next = page = ''

        for item in items:
            try:
                name = item['name']
                id = str(item['id'])
                image = self.tm_img_link % item['profile_path'] if item['profile_path'] else self.fallback_img
                job = item['known_for_department']
                known_for = ', '.join([k.get('title', k.get('name')) for k in item['known_for']])
                info = '[I]%s[/I][CR][CR]Known for: [I]%s[/I]' % (job, known_for)

                self.list.append({'name': name, 'id': id, 'image': image, 'plot': info, 'page': page, 'next': next})
            except:
                log_utils.log('person_fail', 1)
                pass

        return self.list


    def getPeople(self, name, url):
        try:
            while True:
                select = control.selectDialog(['Movies', 'TV Shows', 'Biography'], heading=name)
                if select == -1:
                    break
                elif select == 0:
                    from resources.lib.indexers import movies
                    return movies.movies().get(self.person_movie_link % url)
                elif select == 1:
                    from resources.lib.indexers import tvshows
                    return tvshows.tvshows().get(self.person_tv_link % url)
                elif select == 2:
                    self.bio_txt(url, name)
        except:
            log_utils.log('getPeople', 1)
            pass


    def addDirectory(self, items, content):
        from sys import argv
        if not items:
            control.idle()
            control.infoDialog('No content')

        sysaddon = argv[0]

        syshandle = int(argv[1])

        addonFanart, addonThumb, artPath = control.addonFanart(), control.addonThumb(), control.artPath()

        playRandom = control.lang(32535)

        nextMenu = control.lang(32053)

        kodiVersion = control.getKodiVersion()

        list_items = []
        for i in items:
            try:
                name = i['name']

                plot = i['plot'] or '[CR]'

                if i['image'].startswith('http'): thumb = i['image']
                elif not artPath == None: thumb = os.path.join(artPath, i['image'])
                else: thumb = addonThumb

                cm = []

                if content == 'movies':
                    link = urllib_parse.quote_plus(self.person_movie_link % i['id'])
                    cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=movie&url=%s)' % (sysaddon, link)))
                    url = '%s?action=movies&url=%s' % (sysaddon, link)
                elif content == 'tvshows':
                    link = urllib_parse.quote_plus(self.person_tv_link % i['id'])
                    cm.append((playRandom, 'RunPlugin(%s?action=random&rtype=show&url=%s)' % (sysaddon, link)))
                    url = '%s?action=tvshows&url=%s' % (sysaddon, link)
                else:
                    url = '%s?action=personsSelect&name=%s&url=%s' % (sysaddon, urllib_parse.quote_plus(name), urllib_parse.quote_plus(i['id']))

                try: item = control.item(label=name, offscreen=True)
                except: item = control.item(label=name)

                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': thumb, 'fanart': addonFanart})

                if cm:
                    item.addContextMenuItems(cm)

                if kodiVersion < 20:
                    item.setInfo(type='video', infoLabels={'plot': plot})
                else:
                    vtag = item.getVideoInfoTag()
                    vtag.setMediaType('video')
                    vtag.setPlot(plot)

                #control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
                list_items.append((url, item, True))
            except:
                log_utils.log('people_dir', 1)
                pass

        try:
            next = items[0]['next']
            if next == '': raise Exception()

            icon = control.addonNext()
            url = '%s?action=persons&url=%s&content=%s' % (sysaddon, urllib_parse.quote_plus(next), content)

            if 'page' in items[0] and items[0]['page']: nextMenu += '[I] (%s)[/I]' % str(int(items[0]['page']) + 1)

            try: item = control.item(label=nextMenu, offscreen=True)
            except: item = control.item(label=nextMenu)

            item.setArt({'icon': icon, 'thumb': icon, 'poster': icon, 'banner': icon, 'fanart': addonFanart})
            item.setProperty('SpecialSort', 'bottom')

            #control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
            list_items.append((url, item, True))
        except:
            pass

        control.addItems(handle=syshandle, items=list_items, totalItems=len(list_items))
        control.content(syshandle, '')
        control.directory(syshandle, cacheToDisc=True)

