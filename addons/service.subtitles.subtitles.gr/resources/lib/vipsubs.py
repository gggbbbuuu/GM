# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import print_function, division

from resources.lib.tools import multichoice, cache_method, cache_duration
from contextlib import closing
import zipfile, re, sys, traceback, os
from tulip import control, client
from tulip.log import log_debug
from tulip.compat import unquote_plus, quote_plus, urlparse, urlopen, Request, BytesIO, py3_dec, unquote
from tulip.parsers import itertags_wrapper
from tulip.user_agents import randomagent


class Vipsubs:

    def __init__(self):

        self.list = []; self.data = []
        self.base_link = 'https://vipsubs.gr'
        self.search_movie = ''.join([self.base_link, '/search/{0}/'])
        self.search_show = ''.join([self.base_link, '/?s={0}'])

    @cache_method(cache_duration(440))
    def get(self, query):

        query = py3_dec(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())

            match = re.findall(
                r'(.+?)(?: -)?[ \.](?:\(?(\d{4})\)?|S?(\d{1,2})X?(?: |\.)?E?P?(\d{1,2})(?: \. (.+))?)', query,
                flags=re.I
            )

            if match:

                query, year, season, episode, episode_title = match[0]

                search = quote_plus(' '.join([query, 's', season, 'e', episode, episode_title]))

                url = self.search_show.format(search)

            else:

                url = self.search_movie.format(quote_plus(query))

            self.data = [client.request(url, timeout=control.setting('timeout'))]

            try:
                _next_button = client.parseDOM(self.data[0], 'a', attrs={'class': 'next page-numbers'}, ret='href')[0]
            except IndexError:
                _next_button = None

            while _next_button:

                self.data.append(client.request(_next_button, timeout=control.setting('timeout')))

                try:
                    _next_button = client.parseDOM(self.data[-1], 'a', attrs={'class': 'next page-numbers'}, ret='href')[0]
                    control.sleep(200)
                except IndexError:
                    _next_button = None
                    break

            html = '\n'.join(self.data)

            items = client.parseDOM(html, 'div', attrs={'class': 'article__summary'})

            if not items:
                log_debug('Vipsubs.gr did not provide any results')
                return

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Vipsubs.gr failed at get function, reason: ' + str(e))

            return

        for item in items:

            try:

                label = itertags_wrapper(item, 'a', attrs={'rel': "bookmark"})[0].text

                label = client.replaceHTMLCodes(label)

                url = itertags_wrapper(item, 'a', ret='href')[-1]
                if 'vipsubs.gr' in url:
                    continue
                rating = 10.0

                self.list.append(
                    {
                        'name': label, 'url': url, 'source': 'vipsubs', 'rating': rating, 'title': label,
                        'downloads': '1000'
                    }
                )

            except Exception as e:

                _, __, tb = sys.exc_info()

                print(traceback.print_tb(tb))

                log_debug('Vipsubs.gr failed at self.list formation function, reason: ' + str(e))

                return

        return self.list

    def download(self, path, url):

        if url.startswith('http'):

            log_debug('Vipsubs.gr: Attempting downloading from this url: {0}'.format(url))

            _filename = unquote('.'.join(urlparse(url).path.split('/')[3:5]))
            filename = control.join(path, _filename)

        else:

            filename = control.join(path, url)

        try:

            if url.startswith('http'):

                if 'dropbox' in url:
                    url = client.request(url, output='geturl', timeout=control.setting('timeout'))

                req = Request(url)
                req.add_header('User-Agent', randomagent())
                opener = urlopen(req)
                data = opener.read()
                zip_file = zipfile.ZipFile(BytesIO(data))
                opener.close()

                if control.setting('keep_zips') == 'true':

                    if control.setting('output_folder').startswith('special://'):
                        output_path = control.transPath(control.setting('output_folder'))
                    else:
                        output_path = control.setting('output_folder')
                    if not os.path.exists(output_path):
                        control.makeFile(output_path)
                    # noinspection PyUnboundLocalVariable
                    output_filename = control.join(output_path, _filename)
                    with open(output_filename, 'wb') as f:
                        f.write(data)

                    if control.setting('extract') == 'true':
                        zip_file = zipfile.ZipFile(output_filename)
                        output_path = control.join(output_path, os.path.splitext(_filename)[0])
                        if not os.path.exists(output_path):
                            control.makeFile(output_path)
                        zip_file.extractall(output_path)

                    control.infoDialog(control.lang(30007))

            else:

                if zipfile.is_zipfile(filename):
                    zip_file = zipfile.ZipFile(filename)
                else:
                    log_debug('Failed to load zip with regular python library, attempting built-in method')
                    control.execute('Extract({0},{1})'.format(filename, path))
                    zip_file = None

            if zip_file:

                files = zip_file.namelist()
                subs = [i for i in files if i.endswith(('.srt', '.sub', '.zip'))]

            else:

                subs = []
                for root, _, file_ in os.walk(path):
                    for f in file_:
                        subs.append(os.path.join(root, f))

            subtitle = multichoice(subs)

            if not subtitle:
                return

            if zip_file:

                try:
                    zip_file.extract(subtitle, path)
                except Exception:
                    path = path.encode('utf-8')
                    zip_file.extract(subtitle, path)

            subtitle = control.join(path, subtitle)

            if subtitle.endswith('.zip'):

                return self.download(path, subtitle)

            else:

                try:

                    with closing(control.openFile(subtitle)) as fn:

                        try:
                            output = bytes(fn.readBytes())
                        except Exception:
                            output = bytes(fn.read())

                    content = output.decode('utf-16')

                    with closing(control.openFile(subtitle, 'w')) as subFile:
                        subFile.write(bytearray(content.encode('utf-8')))

                except Exception:
                    pass

                return subtitle

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Vipsubs.gr subtitle download failed for the following reason: ' + str(e))

            return
