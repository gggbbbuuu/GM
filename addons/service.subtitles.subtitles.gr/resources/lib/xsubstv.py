# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import print_function

import re, traceback, sys
from os.path import split as os_split
from os import rename
from tulip.compat import urlencode, zip, py3_dec
from tulip import cleantitle, client, control
from tulip.log import log_debug
from resources.lib.tools import cache_method, cache_duration


class Xsubstv:

    def __init__(self):

        self.list = []
        self.base_link = 'http://www.xsubs.tv'
        self.user = control.setting('xsubstv.user')
        self.password = control.setting('xsubstv.pass')

    @cache_method(cache_duration(440))
    def get(self, query):

        query = py3_dec(query)

        try:

            try:
                title, season, episode = re.findall(r'(.+?)[ .]s?(\d{1,2})(?: |.)?(?:ep?|x|\.)?(\d{1,2})?', query, flags=re.I)[0]
            except (IndexError, TypeError):
                log_debug("Search query is not a tv show related, xsubs.tv does not offer subs for movies")
                return

            if season.startswith('0'):
                season = season[-1]

            title = re.sub(r'^THE\s+|^A\s+', '', title.strip().upper())
            title = cleantitle.get(title)

            url = ''.join([self.base_link, '/series/all.xml'])

            srsid = self.cache(url)
            srsid = [i[0] for i in srsid if title == i[1]][0]

            url = ''.join([self.base_link, '/series/{0}/main.xml'.format(srsid)])

            result = client.request(url)

            try:
                ssnid = client.parseDOM(result, 'series_group', ret='ssnid', attrs={'ssnnum': season})[0]
            except IndexError:
                return

            url = ''.join([self.base_link, '/series/{0}/{1}.xml'.format(srsid, ssnid)])

            result = client.request(url)

            items = client.parseDOM(result, 'subg')
            items = [(client.parseDOM(i, 'etitle', ret='number'), i) for i in items]
            items = [i[1] for i in items if len(i[0]) > 0 and i[0][0] == episode][0]
            items = re.findall('(<sr .+?</sr>)', items)

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Xsubs.tv failed at get function, reason: ' + str(e))

            return

        for item in items:

            try:

                p = client.parseDOM(item, 'sr', ret='published_on')[0]

                if p == '':

                    continue

                name = client.parseDOM(item, 'sr')[0]
                name = name.rsplit('<hits>', 1)[0]
                label = re.sub('</.+?><.+?>|<.+?>', ' ', name).strip()
                label = client.replaceHTMLCodes(label)
                name = '{0} {1}'.format(client.replaceHTMLCodes(query), label)
                name = name.encode('utf-8')

                url = client.parseDOM(item, 'sr', ret='rlsid')[0]
                url = ''.join([self.base_link, '/xthru/getsub/{0}'.format(url)])
                url = client.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                downloads = client.parseDOM(item, 'hits')[0]

                self.list.append(
                    {'name': name, 'url': url, 'source': 'xsubstv', 'rating': 5, 'downloads': downloads, 'title': label}
                )

            except Exception as e:

                _, __, tb = sys.exc_info()

                print(traceback.print_tb(tb))

                log_debug('Xsubs.tv failed at self.list formation function, reason:  ' + str(e))

                return

        return self.list

    @cache_method(cache_duration(2880))
    def cache(self, url):

        try:

            result = client.request(url)
            result = re.sub(r'[^\x00-\x7F]+', ' ', result)

            result = list(zip(client.parseDOM(result, 'series', ret='srsid'), client.parseDOM(result, 'series')))
            result = [(i[0], cleantitle.get(i[1])) for i in result]

            return result

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Xsubs.tv failed at cache function, reason:  ' + str(e))

            return

    @cache_method(cache_duration(720))
    def cookie(self):

        try:

            login = ''.join([self.base_link, '/xforum/account/signin/'])

            token = client.request(login)
            token = client.parseDOM(token, 'input', ret='value', attrs={'name': 'csrfmiddlewaretoken'})[0]

            headers = {'Cookie': 'csrftoken={0}'.format(token)}

            post = {'username': self.user, 'password': self.password, 'csrfmiddlewaretoken': token, 'next': ''}
            post = urlencode(post)

            c = client.request(login, post=post, headers=headers, output='cookie')

            return c

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Xsubs.tv failed at cookie function, reason: ' + str(e))

            return

    def download(self, path, url):

        try:

            log_debug('Xsubs.tv: Attempting downloading from this url: {0}'.format(url))

            cookie = None

            anonymous = (self.user == '' or self.password == '')

            code, result = client.request(url, output='response', error=True)

            if code == '429' and anonymous is True:

                control.dialog.ok(str('xsubs.tv'), str(result), str(''))

                return

            elif anonymous is False:

                cookie = self.cookie()

            result, headers, content, cookie = client.request(url, cookie=cookie, output='extended', as_bytes=True)

            subtitle = content['Content-Disposition']
            subtitle = re.findall('"(.+?)"', subtitle)[0]

            try:
                subtitle = subtitle.decode('utf-8')
            except Exception:
                pass

            subtitle = control.join(path, subtitle)

            if not subtitle.endswith('.srt'):
                raise Exception()

            with open(subtitle, 'wb') as subFile:
                subFile.write(result)

            fileparts = os_split(subtitle)[1].split('.')
            result = control.join(os_split(subtitle)[0], 'subtitles.' + fileparts[len(fileparts)-1])

            rename(subtitle, result)

            return result

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Xsubstv subtitle download failed for the following reason: ' + str(e))

            return
