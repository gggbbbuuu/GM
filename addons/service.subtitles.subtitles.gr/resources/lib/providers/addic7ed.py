# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Addic7ed provider. Series only, English only.

    Exists solely as the English source for the translation fallback: the
    site carries no Greek at all, so it is never queried for Greek results.
    Search and download need no account.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import sys
import traceback
import zipfile
from io import BytesIO
from urllib.parse import quote_plus, unquote_plus

from resources.lib.utils import impersonate
from resources.lib.utils.tools import (
    Cancelled, pick, cache_method, cache_duration, clean_title
)
from tulip import kodi as control
from tulip.cleantitle import replaceHTMLCodes
from tulip.log import log as log_debug


class Addic7ed:

    def __init__(self):

        self.list = []
        self.base_link = 'https://www.addic7ed.com'
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

    @staticmethod
    def _split(query):

        query = str(query)

        if '/imdb=' in query:
            query, _imdb = query.split('/imdb=', 1)

        return query.strip()

    def _get(self, url, timeout):

        '''One page through the impersonating transport (or None).'''

        sess = impersonate.session(timeout=timeout)

        if sess is None:
            return None

        try:
            response = sess.get(
                url, headers={'Referer': self.base_link + '/'}, timeout=timeout
            )
        except Exception as e:
            log_debug('Addic7ed page request failed: ' + str(e))
            return None
        finally:
            impersonate.close(sess)

        if response.status_code != 200 or not response.text:
            return None

        return response.text

    @cache_method(cache_duration(440))
    def _show_id(self, title):

        '''
        Resolves a show title to its numeric id through the homepage
        dropdown, which lists every show on the site.
        '''

        timeout = int(control.setting('timeout'))

        page = self._get(self.base_link + '/', timeout)

        if not page:
            return None

        wanted = clean_title(title)

        for show_id, name in re.findall(
            r'<option value="(\d+)"[^>]*>([^<]+)</option>', page
        ):
            if clean_title(replaceHTMLCodes(name)) == wanted:
                return show_id

        return None

    @cache_method(cache_duration(440))
    def get(self, query):

        self.list = []
        query = self._split(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())
            query = re.sub(r'\bS(\d{1,2})\s+E(\d{1,2})\b', r'S\1E\2', query, flags=re.I)
            timeout = int(control.setting('timeout'))

            match = re.findall(r'^(?P<title>.+)\s+S(\d+)E(\d+)', query, flags=re.I)

            if not match:
                log_debug('Addic7ed offers subtitles for series only')
                return self.list

            title, season, episode = match[0][0].strip(), int(match[0][1]), int(match[0][2])

            show_id = self._show_id(title)

            if show_id is None:
                log_debug('Addic7ed knows no show matching: ' + title)
                return self.list

            table = self._get(
                '{0}/ajax_loadShow.php?show={1}&season={2}&langs=&hd=&hi='.format(
                    self.base_link, show_id, season
                ),
                timeout
            )

            if not table:
                log_debug('Addic7ed season table could not be read')
                return self.list

            rows = re.findall(r'<tr class="epeven[^"]*">(.*?)</tr>', table, flags=re.S)
            found = []

            for row in rows:
                cells = re.findall(r'<td[^>]*>([\s\S]*?)</td>', row)

                if len(cells) < 10:
                    continue

                try:
                    row_season, row_episode = int(cells[0]), int(cells[1])
                except (TypeError, ValueError):
                    continue

                if row_season != season or row_episode != episode:
                    continue

                if 'English' not in cells[3]:
                    continue

                href = re.search(r'href="((?:/original|/updated)/[^"]+)"', row)

                if not href:
                    continue

                version = re.sub(r'<.+?>', '', cells[4]).strip()
                impaired = 'hi.PNG' in row

                name = u'{0} S{1:02d}E{2:02d} English'.format(title, season, episode)

                if version:
                    name += u' ' + replaceHTMLCodes(version)

                found.append(
                    (self.base_link + href.group(1), name, impaired)
                )

            if not found:
                log_debug('Addic7ed episode has no English subtitles')
                return self.list

        except Cancelled:

            log_debug('Addic7ed download cancelled by user')

            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Addic7ed failed at get function, reason: ' + str(e))

            return

        for url, name, impaired in found:

            try:

                self.list.append(
                    {
                        'name': name, 'url': url, 'source': 'addic7ed',
                        'rating': 3, 'title': name, 'downloads': '0',
                        'hearing_imp': 'true' if impaired else 'false',
                    }
                )

            except Cancelled:

                log_debug('Addic7ed download cancelled by user')

                return

            except Exception as e:

                log_debug('Addic7ed failed at self.list formation function, reason: ' + str(e))

                continue

        return self.list

    def download(self, path, url):

        try:

            timeout = int(control.setting('download_timeout'))

            sess = impersonate.session(timeout=timeout)

            if sess is None:
                log_debug('Addic7ed download needs script.module.curlcffi, skipping')
                return

            try:
                data = sess.get(
                    unquote_plus(url), headers={'Referer': self.base_link + '/'}, timeout=timeout
                ).content
            finally:
                impersonate.close(sess)

            if data[:2] == b'PK':
                return self._extract_zip(path, data)

            if b'-->' not in data[:400]:
                raise Exception('Addic7ed did not return a subtitle')

            filename = 'addic7ed.srt'

            target = control.join(path, filename)

            with open(target, 'wb') as subFile:
                subFile.write(data)

            return target

        except Cancelled:

            log_debug('Addic7ed download cancelled by user')

            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Addic7ed subtitle download failed for the following reason: ' + str(e))

            return

    @staticmethod
    def _extract_zip(path, data):

        zip_file = zipfile.ZipFile(BytesIO(data))
        subs = [i for i in zip_file.namelist() if i.lower().endswith(('.srt', '.sub'))]

        if not subs:
            raise Exception('no subtitles inside archive')

        subtitle = pick(subs)

        with zip_file.open(subtitle) as source:
            raw = source.read()

        target = control.join(path, subtitle)

        with open(target, 'wb') as subFile:
            subFile.write(raw)

        return target
