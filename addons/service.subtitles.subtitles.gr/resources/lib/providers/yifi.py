# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    YIFI provider, ported from service.subtitles.greeksubs
    by Bugatsinho and rewritten to tulip idioms. Movies only.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import sys
import json
import traceback
import zipfile

from resources.lib.utils.tools import Cancelled, pick, cache_method, cache_duration, randomagent
from tulip import cleantitle
from tulip import kodi as control
from netclient import Net
from domparsers import parseDOM
from tulip.cleantitle import replaceHTMLCodes
from urllib.parse import quote_plus, unquote_plus
from urllib.request import urlopen, Request
from io import BytesIO
from tulip.log import log as log_debug


class Yifi:

    def __init__(self):

        self.list = []
        self.base_link = 'https://yifysubtitles.ch/'
        self.detail_link = 'https://yifysubtitles.org/'
        self.ajax = 'ajax/search/?mov={0}'
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
        )

    @staticmethod
    def _split(query):

        query = str(query)

        if '/imdb=' in query:
            query, imdb = query.split('/imdb=', 1)
        else:
            imdb = '0'

        return query.strip(), imdb.strip()

    @staticmethod
    def _text(result):

        try:
            return result.decode('utf-8', errors='replace')
        except AttributeError:
            return result

    @staticmethod
    def _absolute(base, href):

        href = replaceHTMLCodes(href)

        if href.startswith('http'):
            return href

        return base.rstrip('/') + '/' + href.lstrip('/')

    @cache_method(cache_duration(440))
    def get(self, query):

        self.list = []
        query, imdb = self._split(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())

            match = re.findall(r'^(?P<title>.+)[\s+\(|\s+](?P<year>\d{4})', query)

            if len(match) == 0:
                log_debug('Yifi offers subtitles for movies only')
                return self.list

            title, year = match[0][0].strip(), match[0][1]
            timeout = int(control.setting('timeout'))

            if not imdb.startswith('tt'):

                ajax = self.base_link + self.ajax.format(quote_plus(title))
                entries = json.loads(self._text(Net(user_agent=randomagent(), timeout=timeout).http_GET(
                    ajax
                ).nodecode(True).content.decode('utf-8', errors='replace')))

                try:
                    imdb = next(
                        i['imdb'] for i in entries
                        if cleantitle.get(i['movie']) == cleantitle.get('{0} {1}'.format(title, year))
                    )
                except StopIteration:
                    log_debug('Yifi did not provide any results')
                    return self.list

            result = self._text(
                Net(user_agent=randomagent(), timeout=timeout).http_GET(
                    self.detail_link + 'movie-imdb/' + imdb
                ).nodecode(True).content.decode('utf-8', errors='replace')
            )

            rows = parseDOM(result, 'tr', attrs={'data-id': r'\d+'})
            rows = [i for i in rows if 'greek' in i.lower()]

            if not rows:
                log_debug('Yifi did not provide any results')
                return self.list

            urls = []

            for row in rows:

                try:

                    name = parseDOM(row, 'a')[0]
                    name = re.sub(r'<.+?>', '', name).replace('subtitle', '')
                    name = replaceHTMLCodes(name).strip()

                    href = parseDOM(row, 'a', ret='href')[0]
                    href = replaceHTMLCodes(href)

                    urls.append((name, href))

                except Exception:
                    continue

        except Cancelled:

            log_debug('Yifi download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Yifi failed at get function, reason: ' + str(e))

            return

        for name, href in urls:

            try:

                subpage = self._text(Net(user_agent=randomagent(), timeout=timeout).http_GET(
                    self._absolute(self.detail_link, href)
                ).nodecode(True).content.decode('utf-8', errors='replace'))
                dl = parseDOM(
                    subpage, 'a', ret='href', attrs={'class': 'btn-icon download-subtitle'}
                )[0]
                # file endpoint is Cloudflare-gated on .org, served plain on .ch
                dl = self._absolute(self.base_link, replaceHTMLCodes(dl))

                self.list.append(
                    {
                        'name': name, 'url': dl, 'source': 'yifi', 'rating': 5,
                        'title': name, 'downloads': '0'
                    }
                )

            except Exception as e:

                log_debug('Yifi failed at self.list formation function, reason: ' + str(e))

                continue

        return self.list

    def download(self, path, url):

        try:

            timeout = int(control.setting('download_timeout'))

            req = Request(url)
            req.add_header('User-Agent', randomagent())

            referer = url.replace('/subtitle/', '/subtitles/')
            if referer.endswith('.zip'):
                referer = referer[:-4]
            req.add_header('Referer', referer)

            data = urlopen(req, timeout=timeout).read()

            filename = unquote_plus(url.rpartition('/')[2].split('?')[0]) or 'subtitle.zip'
            filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
            f = control.join(path, filename)

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
                    log_debug('Yifi could not extract subtitle from archive')
                    return

                subtitle = pick(filenames)
                control.deleteFile(f)

                return control.join(path, subtitle)

        except Cancelled:

            log_debug('Yifi download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Yifi subtitle download failed for the following reason: ' + str(e))

            return
