# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SubDL provider. Movies and series, Greek only.

    subdl.com sits behind Cloudflare, which rejects the TLS fingerprint of
    python-urllib outright, so the HTML title pages are read through the
    TLS-impersonating transport. The public read API and the file host are not
    challenged, so those go through the ordinary stack.

    SubDL publishes Greek subtitles in windows-1253, so archived entries are
    converted to UTF-8 on the way out; Kodi renders the raw bytes as mojibake.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import sys
import json
import zipfile
import traceback
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from urllib.parse import quote_plus, unquote_plus

from resources.lib.utils import impersonate
from resources.lib.utils.tools import Cancelled, pick, cache_method, cache_duration, randomagent
from tulip import kodi as control
from tulip.log import log as log_debug
from tulip.cleantitle import replaceHTMLCodes


class Subdl:

    def __init__(self):

        self.list = []
        self.base_link = 'https://subdl.com'
        self.dl_link = 'https://dl.subdl.com'
        self.api_link = 'https://api2.subdl.com'
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

    @staticmethod
    def _seasons():
        '''
        SubDL names season pages with ordinal words rather than numbers.
        '''

        names = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh',
                 'eighth', 'ninth', 'tenth']

        seasons = {'{0}-season'.format(n): i for i, n in enumerate(names, 1)}

        seasons['specials-season'] = 0

        return seasons

    @staticmethod
    def _split(query):

        query = str(query)

        if '/imdb=' in query:
            query, _imdb = query.split('/imdb=', 1)
        else:
            _imdb = '0'

        return query.strip(), _imdb.strip()

    @staticmethod
    def _text(result):

        try:
            return result.decode('utf-8', errors='replace')
        except AttributeError:
            return result

    @staticmethod
    def _words(text):

        return set(re.sub(r'[^a-z0-9 ]', '', str(text).lower()).split())

    def _api_search(self, keyword, timeout):

        '''
        The public read API needs no credentials and accepts either a title or
        a bare imdb id, so this returns a list of result dicts.
        '''

        url = '{0}/search?query={1}'.format(self.api_link, quote_plus(keyword))

        req = Request(url, headers={'User-Agent': randomagent(),
                                    'Accept': 'application/json',
                                    'Referer': self.base_link + '/'})

        try:
            body = urlopen(req, timeout=timeout).read().decode('utf-8', errors='replace')
        except Exception as e:
            log_debug('Subdl search API failed: ' + str(e))
            return []

        try:
            return json.loads(body).get('results') or []
        except Exception as e:
            log_debug('Subdl search API returned unusable data: ' + str(e))
            return []

    def _pick(self, results, title, year, is_series):

        '''Chooses the best matching entry out of the API results.'''

        wanted = self._words(re.sub(r'^(THE|A)\s+', '', title.upper()))

        best = None
        best_score = -1

        for res in results:

            if is_series and res.get('type') not in ('tv', 'series'):
                continue

            if not is_series and res.get('type') != 'movie':
                continue

            name = self._words(res.get('name') or res.get('original_name') or '')

            if not name:
                continue

            score = len(wanted & name) * 2 - abs(len(wanted) - len(name))

            if year and res.get('year'):

                try:
                    gap = abs(int(res['year']) - int(year))
                    score -= gap * 3
                except (TypeError, ValueError):
                    pass

            if score > best_score:

                best_score = score
                best = res

        if best is None and not is_series:
            # movies fall back to any type, the title may be filed as a series
            for res in results:
                if res.get('type') != 'movie':
                    continue
                name = self._words(res.get('name') or res.get('original_name') or '')
                if name and len(wanted & name):
                    return res

        return best

    def _page(self, url, timeout):

        '''Reads one HTML page through the impersonating transport.'''

        sess = impersonate.session(timeout=timeout)

        if sess is None:
            log_debug('Subdl needs script.module.curlcffi for title pages, skipping')
            return None

        try:
            response = sess.get(url, headers={'Referer': self.base_link + '/'}, timeout=timeout)
        except Exception as e:
            log_debug('Subdl page request failed: ' + str(e))
            return None
        finally:
            impersonate.close(sess)

        if response.status_code != 200:
            log_debug('Subdl page returned HTTP {0}: {1}'.format(response.status_code, url))
            return None

        return response.text

    @staticmethod
    def _greek_block(page, language='greek'):

        '''
        Each language on a title page is wrapped in its own
        data-language container, so Greek can be lifted out without touching
        the other 40-odd languages.
        '''

        blocks = re.split(r'data-language="([a-z\-]+)"', page)

        for i in range(1, len(blocks), 2):

            if blocks[i] == language:
                return blocks[i + 1]

        return ''

    @staticmethod
    def _entries(block, episode=None):

        '''
        Reads the subtitle rows out of one language block.

        Each row carries the download href plus data-episode-from/-to, and
        whole-season packs are flagged with data-full-season.
        '''

        rows = re.findall(
            r'<li[^>]*data-n-id="[A-Za-z0-9]+"([^>]*)>([\s\S]*?)</li>', block
        )

        found = []

        for attrs, body in rows:

            if 'data-subtitle-download' not in body:
                continue

            href = re.search(r'data-subtitle-download href="([^"]+)"', body)
            title = re.search(r'data-subtitle-title[^>]*>\s*<h4>([^<]+)</h4>', body)

            if not href or not title:
                continue

            name = replaceHTMLCodes(title.group(1)).strip()

            ep_from = re.search(r'data-episode-from="([^"]*)"', attrs)
            ep_to = re.search(r'data-episode-to="([^"]*)"', attrs)
            downloads = re.search(r'data-downloads="(\d+)"', attrs)

            try:
                ep_from = int(ep_from.group(1)) if ep_from else 0
            except (TypeError, ValueError):
                ep_from = 0

            try:
                ep_to = int(ep_to.group(1)) if ep_to else 0
            except (TypeError, ValueError):
                ep_to = 0

            impaired = 'data-hi' in attrs

            # SubDL stamps data-full-season onto rows that still carry a single
            # episode's range, so the flag cannot be trusted on its own. A row
            # counts as a pack only when it spans more than one episode or
            # declares no episode at all.
            full_season = ep_from <= 0 or ep_to > ep_from

            if episode is not None and not full_season:

                if not (ep_from <= episode <= ep_to):
                    continue

            found.append(
                {
                    'url': replaceHTMLCodes(href.group(1)),
                    'name': name,
                    'episode_from': ep_from,
                    'episode_to': ep_to,
                    'full_season': full_season,
                    'impaired': impaired,
                    'downloads': downloads.group(1) if downloads else '0',
                }
            )

        return found

    def _series_page(self, entry, season, timeout):

        '''Resolves the season page for a series entry.'''

        link = entry.get('link') or ''

        page = self._page(self.base_link + link, timeout)

        if not page:
            return None

        seasons = self._seasons()

        # already a season page, or the series has a single page of subtitles
        if season in seasons and self._greek_block(page):
            return page

        matches = re.findall(
            r'href="(' + re.escape(link) + r'/([a-z0-9\-]+))"', page
        )

        for href, name in matches:

            number = seasons.get(name)

            if number is None:
                continue

            if number == season:
                return self._page(self.base_link + href, timeout)

        return None

    @cache_method(cache_duration(440))
    def get(self, query, language='greek'):

        self.list = []

        try:

            query, _imdb = self._split(query)

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())

            season = episode = None
            hdlr = re.search(r'\bS(\d{1,2})[\s.]?E(\d{1,2})\b', query, flags=re.I)

            if hdlr:
                season, episode = int(hdlr.group(1)), int(hdlr.group(2))
                query = re.sub(hdlr.group(0), ' ', query)

            title, year = self._parse_title(query)

            if not title:
                log_debug('Subdl could not make sense of the query: ' + query)
                return self.list

            timeout = int(control.setting('timeout'))
            is_series = season is not None

            keyword = _imdb if _imdb.isdigit() and len(_imdb) > 3 else '{0} {1}'.format(title, year).strip()

            results = self._api_search(keyword, timeout)

            if not results:
                log_debug('Subdl did not provide any results')
                return self.list

            entry = self._pick(results, title, year, is_series)

            if entry is None:
                log_debug('Subdl found no entry matching: ' + title)
                return self.list

            link = entry.get('link')

            if not link:
                return self.list

            if is_series:
                page = self._series_page(entry, season, timeout)
            else:
                page = self._page(self.base_link + link, timeout)

            if not page:
                log_debug('Subdl title page could not be read')
                return self.list

            block = self._greek_block(page, language)

            if not block:
                log_debug('Subdl has no {0} subtitles for: {1}'.format(language, title))
                return self.list

            entries = self._entries(block, episode if is_series else None)

            if not entries:
                log_debug('Subdl {0} list held no usable entries'.format(language))
                return self.list

        except Cancelled:

            log_debug('Subdl download cancelled by user')

            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Subdl failed at get function, reason: ' + str(e))

            return

        for entry in entries:

            try:

                self.list.append(
                    {
                        'name': entry['name'],
                        'url': entry['url'],
                        'source': 'subdl_tr' if language != 'greek' else 'subdl',
                        'rating': self._rating(entry['downloads']),
                        'title': entry['name'],
                        'downloads': entry['downloads'],
                        'hearing_imp': 'true' if entry['impaired'] else 'false',
                    }
                )

            except Cancelled:

                log_debug('Subdl download cancelled by user')

                return

            except Exception as e:

                log_debug('Subdl failed at self.list formation function, reason: ' + str(e))

                continue

        return self.list

    @staticmethod
    def _parse_title(query):

        '''
        Returns the bare title and, when present, the year.
        '''

        match = re.findall(r'^(?P<title>.+?)[\s+\(]*(?P<year>\d{4})?\s*$', query)

        if not match:
            return None, None

        title = match[0][0].strip()
        year = match[0][1].strip() if len(match[0]) > 1 else None

        # leftover SxxExx noise or a bare 'Season 2'
        title = re.sub(r'\bseason\b\s*\d+', ' ', title, flags=re.I).strip()

        if not title:
            return None, None

        return title, year

    @staticmethod
    def _rating(downloads):

        try:
            rating = int(downloads)
        except (TypeError, ValueError):
            rating = 0

        if rating < 100:
            rating = 1
        elif rating < 200:
            rating = 2
        elif rating < 300:
            rating = 3
        elif rating < 400:
            rating = 4
        else:
            rating = 5

        return rating

    def download(self, path, url):

        try:

            timeout = int(control.setting('download_timeout'))

            url = unquote_plus(url)

            if not url.startswith('http'):
                url = self.dl_link + '/' + url.lstrip('/')

            req = Request(url, headers={'User-Agent': randomagent(),
                                        'Accept': '*/*',
                                        'Referer': self.base_link + '/'})

            try:
                data = urlopen(req, timeout=timeout).read()
            except HTTPError as e:
                # the file host is not challenged, but fall back to impersonation
                sess = impersonate.session(timeout=timeout)

                if sess is None:
                    raise

                try:
                    data = sess.get(
                        url, headers={'Referer': self.base_link + '/'}, timeout=timeout
                    ).content
                finally:
                    impersonate.close(sess)

            if data[:4] != b'PK\x03\x04':
                raise Exception('Subdl did not return an archive')

            filename = re.sub(r'[\\/:*?"<>|]', '_', url.rpartition('/')[2].split('?')[0])
            filename = filename or 'subtitle.zip'

            return self._extract(path, filename, data)

        except Cancelled:

            log_debug('Subdl download cancelled by user')

            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Subdl subtitle download failed for the following reason: ' + str(e))

            return

    def _extract(self, path, filename, data):

        '''Unpacks the archive, converting Greek windows-1253 subs to UTF-8.'''

        zip_file = zipfile.ZipFile(BytesIO(data))
        subs = [i for i in zip_file.namelist() if i.lower().endswith(('.srt', '.sub'))]

        if not subs:
            raise Exception('no subtitles inside archive')

        subtitle = pick(subs)

        with zip_file.open(subtitle) as source:

            raw = source.read()

        target = control.join(path, subtitle)

        with open(target, 'wb') as subFile:
            subFile.write(self._to_utf8(raw))

        return target

    @staticmethod
    def _to_utf8(raw):

        '''
        SubDL serves Greek subs in windows-1253. UTF-8 is tried first because
        some releases genuinely are UTF-8, and the common case of Greek text
        decoding cleanly as windows-1253 always wins.
        '''

        try:
            raw.decode('utf-8')
            return raw
        except UnicodeDecodeError:
            pass

        try:
            return raw.decode('cp1253').encode('utf-8')
        except UnicodeDecodeError:
            return raw