# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Moviesubtitles.org provider. Movies only, Greek only.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import sys
import traceback
import zipfile
from urllib.error import HTTPError

from resources.lib.utils.tools import Cancelled, pick, cache_method, cache_duration, randomagent
from tulip import kodi as control
from netclient import Net
from tulip.cleantitle import replaceHTMLCodes
from urllib.parse import quote_plus, unquote_plus, urlencode
from urllib.request import urlopen, Request
from tulip.log import log as log_debug
from io import BytesIO


class Moviesubs:

    def __init__(self):

        self.list = []
        self.base_link = 'https://www.moviesubtitles.org/'
        self.search_link = self.base_link + 'search.php'
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        )

    @staticmethod
    def _split(query):

        query = str(query)

        if '/imdb=' in query:
            query, _imdb = query.split('/imdb=', 1)

        return query.strip()

    @staticmethod
    def _words(text):

        return set(re.sub(r'[^a-z0-9 ]', '', text.lower()).split())

    def _search(self, title, timeout):

        req = Request(self.search_link, data=urlencode({'q': title}).encode('utf-8'))
        req.add_header('User-Agent', self.user_agent)
        req.add_header('Referer', self.base_link)

        try:
            data = urlopen(req, timeout=timeout).read()
        except HTTPError as e:
            # search answers 500 but still carries the results
            data = e.read()

        return data.decode('utf-8', errors='replace')

    @cache_method(cache_duration(440))
    def get(self, query, language='gr'):

        self.list = []
        query = self._split(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())
            timeout = int(control.setting('timeout'))

            match = re.findall(r'^(?P<title>.+)[\s+\(|\s+](?P<year>\d{4})', query)

            if len(match) == 0:
                log_debug('Moviesubs offers subtitles for movies only')
                return self.list

            title, year = match[0][0].strip(), match[0][1]

            page = self._search(title, timeout)

            movies = re.findall(
                r'<a href="/(movie-\d+[^"]*)">([^<]+?)\s*\((\d{4})\)</a>', page, flags=re.I
            )

            wanted = self._words(title)

            movie = next(
                (
                    href for href, name, y in movies
                    if y == year and wanted <= self._words(replaceHTMLCodes(name))
                ),
                None
            )

            if movie is None:
                log_debug('Moviesubs did not provide any results')
                return self.list

            page = Net(user_agent=self.user_agent, timeout=timeout).http_GET(
                self.base_link + movie
            ).nodecode(True).content.decode('utf-8', errors='replace')

            if isinstance(page, bytes):
                page = page.decode('utf-8', errors='replace')

            blocks = re.findall(
                r'<a href="/(subtitle-\d+\.html)"[^>]*>([\s\S]*?)</a>', page, flags=re.I
            )
            # Greek subtitles only (English when called for translation)
            blocks = [(href, body) for href, body in blocks if 'flags/{0}.gif'.format(language) in body]

            if not blocks:
                log_debug('Moviesubs did not provide any results')
                return self.list

        except Cancelled:

            log_debug('Moviesubs download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Moviesubs failed at get function, reason: ' + str(e))

            return

        for href, block in blocks:

            try:

                name = re.search(r'<b>([\s\S]*?)</b>', block, flags=re.I).groups()[0]
                name = re.sub(r'<.+?>', '', name).strip()
                name = replaceHTMLCodes(name)

                try:
                    downloads = re.search(
                        r'downloads\.png[\s\S]{0,200}?<td[^>]*>\s*(\d+)\s*</td>', block, flags=re.I
                    ).groups()[0]
                except (AttributeError, IndexError):
                    downloads = '0'

                downloads = re.sub('[^0-9]', '', downloads) or '0'

                try:
                    bad, good = re.search(
                        r'color:red">(\d+)</span>\s*/\s*<span[^>]*color:green">(\d+)',
                        block, flags=re.I
                    ).groups()
                    total = int(bad) + int(good)
                    rating = max(1, round(5 * int(good) / total)) if total else 5
                except (AttributeError, IndexError, ValueError):
                    rating = 5

                self.list.append(
                    {
                        'name': name, 'url': self.base_link + href,
                        'source': 'moviesubs_tr' if language != 'gr' else 'moviesubs',
                        'rating': rating, 'title': name, 'downloads': downloads
                    }
                )

            except Exception as e:

                log_debug('Moviesubs failed at self.list formation function, reason: ' + str(e))

                continue

        return self.list

    def download(self, path, url):

        try:

            timeout = int(control.setting('download_timeout'))
            headers = {'User-Agent': self.user_agent, 'Referer': url}

            page = Net(user_agent=self.user_agent, timeout=timeout).http_GET(
                url, headers={'Referer': url}
            ).nodecode(True).content.decode('utf-8', errors='replace')

            wait_id = re.search(r'href="(download-\d+\.html)"', page, flags=re.I).groups()[0]

            req = Request(self.base_link + wait_id)
            req.add_header('User-Agent', randomagent())
            req.add_header('Referer', url)

            data = urlopen(req, timeout=timeout).read()

            filename = unquote_plus(wait_id.replace('.html', '.zip'))
            filename = re.sub(r'[\\/:*?"<>|]', '_', filename)

            try:

                zip_file = zipfile.ZipFile(BytesIO(data))
                files = zip_file.namelist()
                subs = [i for i in files if i.endswith(('.srt', '.sub'))]

                if not subs:
                    raise zipfile.BadZipFile('no subtitles inside archive')

                subtitle = pick(subs)
                zip_file.extract(subtitle, path)

                return control.join(path, subtitle)

            except zipfile.BadZipFile:

                f = control.join(path, filename)

                with open(f, 'wb') as subFile:
                    subFile.write(data)

                control.execute('Extract("{0}","{1}")'.format(f, path))

                for _i in range(0, 10):

                    try:

                        _dirs, files = control.listDir(path)

                        if any(i.endswith(('.srt', '.sub')) for i in files):
                            break

                        control.sleep(1000)

                    except Exception:
                        pass

                _dirs, files = control.listDir(path)
                filenames = [i for i in files if i.endswith(('.srt', '.sub'))]

                if not filenames:
                    log_debug('Moviesubs could not extract subtitle from archive')
                    return

                subtitle = pick(filenames)
                control.deleteFile(f)

                return control.join(path, subtitle)

        except Cancelled:

            log_debug('Moviesubs download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Moviesubs subtitle download failed for the following reason: ' + str(e))

            return
