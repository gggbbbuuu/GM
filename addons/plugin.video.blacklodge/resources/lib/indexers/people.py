# -*- coding: utf-8 -*-

"""
    BlackLodge Add-on
"""


from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.modules import cache
from resources.lib.modules import utils
from resources.lib.modules import log_utils
from resources.lib.indexers import navigator

import os, sys, re

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

import six
from six.moves import urllib_parse


params = dict(urllib_parse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()

action = params.get('action')


class People:
    def __init__(self):
        self.list = []

        self.items_per_page = str(control.setting('items.per.page')) or '20'

        self.personlist_link = 'https://www.imdb.com/search/name/?gender=male,female&count=50'
        self.person_search_link = 'https://www.imdb.com/search/name/?name=%s&count=50'
        self.person_movie_link = 'https://www.imdb.com/search/title/?title_type=feature,tv_movie&role=%s&sort=year,desc&count=%s' % ('%s', self.items_per_page)
        self.person_tv_link = 'https://www.imdb.com/search/title/?title_type=tv_series,tv_miniseries&release_date=,date[0]&role=%s&sort=year,desc&count=%s' % ('%s', self.items_per_page)
        self.bio_link = 'https://www.imdb.com/name/%s/bio/'


    def persons(self, url=None, content=''):
        if not url:
            url = self.personlist_link
        #log_utils.log(url)
        self.list = cache.get(self.imdb_person_list, 24, url)
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


    def bio_txt(self, url, name):
        url = self.bio_link % url
        r = cache.get(client.request, 168, url)
        r = six.ensure_text(r)
        r = re.compile('type="application/json">({"props":.+?)</script><script>').findall(r)[0]
        r = utils.json_loads_as_str(r)['props']['pageProps']['contentData']['entityMetadata']
        try:
            born = r['birthDate']['displayableProperty']['value']['plainText']
        except:
            born = ''
        try:
            if r['deathStatus'] == 'DEAD':
                died = r['deathDate']['displayableProperty']['value']['plainText']
            else:
                died = ''
        except:
            died = ''
        try:
            bio = r['bio']['text']['plainText']
        except:
            bio = ''

        txt = '[B]Born:[/B] {0}[CR]{1}[CR]{2}'.format(born or 'N/A', '[B]Died:[/B] {}[CR]'.format(died) if died else '', bio or '[B]Biography:[/B] N/A')
        control.textViewer(text=txt, heading=name, monofont=False)


    def imdb_person_list(self, url):
        count_ = re.findall(r'&count=(\d+)', url)
        if len(count_) == 1 and int(count_[0]) > 250:
            url = url.replace('&count=%s' % count_[0], '&count=250')

        result = client.request(url)
        #log_utils.log(result)

        try:
            data = re.findall('<script id="__NEXT_DATA__" type="application/json">({.+?})</script>', result)[0]
            data = utils.json_loads_as_str(data)
            data = data['props']['pageProps']['searchResults']['nameResults']['nameListItems']
            items = data[-50:]
            #log_utils.log(repr(items))
        except:
            return

        try:
            cur = re.findall(r'&count=(\d+)', url)[0]
            if int(cur) > len(data) or cur == '250':
                items = data[-(len(data) - int(count_[0]) + 50):]
                raise Exception()
            next = re.sub(r'&count=\d+', '&count=%s' % str(int(cur) + 50), url)
            #log_utils.log('next_url: ' + next)
            page = int(cur) // 50
        except:
            #log_utils.log('next_fail', 1)
            next = page = ''

        for item in items:
            try:
                name = item['nameText']
                id = item['nameId']
                image = item.get('primaryImage', {}).get('url')
                if not image or '/sash/' in image or '/nopicture/' in image: image = 'person.png'
                else: image = re.sub(r'(?:_SX|_SY|_UX|_UY|_CR|_AL|_V)(?:\d+|_).+?\.', '_SX500.', image)

                job = ' / '.join([i for i in item['primaryProfessions']])
                known_for = item.get('knownFor', {}).get('originalTitleText') or 'N/A'

                bio = item['bio']
                bio = client.replaceHTMLCodes(bio)
                bio = six.ensure_str(bio, errors='ignore')
                bio = bio.replace('<br/><br/>', '[CR][CR]')
                bio = re.sub(r'<.*?>', '', bio)

                info = '[I]%s[/I][CR]Known for: [I]%s[/I][CR][CR]%s' % (job, known_for, bio)

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

