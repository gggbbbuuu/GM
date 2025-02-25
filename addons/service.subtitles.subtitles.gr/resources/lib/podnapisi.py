# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import print_function, division

import zipfile, re, sys, traceback
from tulip import control, client
from tulip.log import log_debug
from tulip.compat import unquote_plus, quote_plus, urlopen, BytesIO, Request, py3_dec
from tulip.user_agents import randomagent
from resources.lib.tools import cache_method, cache_duration


class Podnapisi:

    def __init__(self):

        self.list = []
        self.base_link = 'https://www.podnapisi.net'
        self.search_link = ''.join([self.base_link, '/en/subtitles/search/'])

    @cache_method(cache_duration(440))
    def get(self, query):

        query = py3_dec(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())

            query_link = '&'.join(
                [
                    'keywords={keywords}', 'movie_type={movie_type}', 'language=!el', 'seasons={seasons}',
                    'episodes={episodes}', 'year={year}', 'type=', 'undefined=auto', 'undefined=en'
                ]
            )

            match = re.findall(
                r'(.+?)(?: -)?[ \.](?:\(?(\d{4})\)?|S?(\d{1,2})X?(?: |\.)?E?P?(\d{1,2})(?: \. (.+))?)', query,
                flags=re.I
            )

            if match:

                query, year, season, episode, episode_title = match[0]

                url = '?'.join(
                    [
                        self.search_link,
                        query_link.format(
                            keywords=quote_plus(query),
                            movie_type='movie' if year and not (season or episode) else 'tv-series',
                            seasons=season, episodes=episode, year=year
                        )
                    ]
                )

            else:

                url = '?'.join(
                    [
                        self.search_link,
                        query_link.format(
                            keywords=quote_plus(query), movie_type='', seasons='', episodes='', year=''
                        )
                    ]
                )

            result = client.request(
                url, headers={'Accept': 'text/html', 'Accept-Language': 'en-US,en;q=0.9,el;q=0.8'},
                timeout=control.setting('timeout'), verify=False
            )

            try:
                result = result.decode('utf-8', errors='replace')
            except AttributeError:
                pass

            items = client.parseDOM(result, 'tr', attrs={'class': 'subtitle-entry'})

            if not items:
                log_debug('Podnapisi.net did not provide any results')
                return

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Podnapisi.net failed at get function, reason: ' + str(e))

            return

        for item in items:

            try:

                if '<span>el</span>' not in item:
                    continue

                table = client.parseDOM(item, 'td')

                try:
                    downloads = [i.strip() for i in table]
                    downloads = [i for i in downloads if i.isdigit()][1]
                except IndexError:
                    downloads = '0'

                downloads = re.sub('[^0-9]', '', downloads)

                label = client.parseDOM(item, 'a', attrs={'alt': 'Subtitles\' page'})[0]
                label = client.replaceHTMLCodes(label)
                name = u'{0} [{1} DLs]'.format(label, downloads)

                url = [i for i in table if 'Download subtitles.' in i][0]
                url = client.parseDOM(url, 'a', ret='href')[0]
                url = ''.join([self.base_link, url])

                rating = [i for i in table if 'progress rating' in i][0]
                rating = client.parseDOM(rating, 'div', attrs={'class': 'progress rating'}, ret='data-title')[0]
                rating = int(rating.partition('.')[0]) / 20

                self.list.append(
                    {
                        'name': name, 'url': url, 'source': 'podnapisi', 'rating': rating, 'title': label,
                        'downloads': downloads
                    }
                )

            except Exception as e:

                _, __, tb = sys.exc_info()

                print(traceback.print_tb(tb))

                log_debug('Podnapisi.net failed at self.list formation function, reason: ' + str(e))

                return

        return self.list

    def download(self, path, url):

        try:

            req = Request(url)
            req.add_header('User-Agent', randomagent())
            opener = urlopen(req)
            data = opener.read()
            zip_file = zipfile.ZipFile(BytesIO(data))
            opener.close()
            files = zip_file.namelist()
            srt = [i for i in files if i.endswith(('.srt', '.sub'))][0]
            subtitle = control.join(path, srt)

            zip_file.extractall(path)

            return subtitle

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Podnapisi.net subtitle download failed for the following reason: ' + str(e))

            return
