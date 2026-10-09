# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    GreekSubs.net provider, ported from service.subtitles.greeksubs
    by Bugatsinho and rewritten to tulip idioms.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import sys
import zipfile
import traceback
from io import BytesIO
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor, build_opener

from resources.lib.utils.tools import Cancelled, pick, cache_method, cache_duration, clean_title
from tulip import kodi as control
from domparsers import parseDOM
from tulip.cleantitle import replaceHTMLCodes
from urllib.parse import quote_plus, unquote_plus, urlencode
from urllib.request import Request
from tulip.log import log as log_debug


class Subztv:

    def __init__(self):

        self.list = []
        self.base_link = 'https://greeksubs.net/'
        self.user_agent = (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
        )

    @staticmethod
    def _split(query):

        query = str(query)

        if '/imdb=' in query:
            query, imdb = query.split('/imdb=', 1)
        else:
            imdb = '0'

        return query.strip(), imdb.strip()

    def _opener(self):

        jar = CookieJar()

        return build_opener(HTTPCookieProcessor(jar)), jar

    def _get(self, opener, url, referer=None, timeout=30):

        req = Request(url)
        req.add_header('User-Agent', self.user_agent)

        if referer:
            req.add_header('Referer', referer)

        data = opener.open(req, timeout=timeout).read()

        return data.decode('utf-8', errors='replace')

    def _cookie(self, jar, name):

        for cookie in jar:
            if cookie.name == name:
                return cookie.value

        return ''

    def _cards(self, opener, keyword, timeout):

        url = self.base_link + 'search/' + quote_plus(keyword)
        page = self._get(opener, url, timeout=timeout)

        cards = re.findall(
            r'<a[^>]*href="(https://greeksubs\.net/view/[^"]+)"[^>]*>'
            r'[\s\S]*?movie-title-tooltip"[^>]*>\s*<div[^>]*>\s*([^<>]+?)\s*</div>',
            page, flags=re.I
        )

        # series cards carry suffixes like "Show (S01 - S05)", strip them
        return [
            (link, re.sub(r'\s*\(.*?\)\s*', ' ', name).strip()) for link, name in cards
        ]

    def _match_card(self, opener, title, timeout):

        '''
        Resolves a search card for the given title.

        The site searches literally, so "The Matrix" finds nothing while
        "Matrix" finds the entry. Retry without the leading article.
        '''

        wanted = clean_title(title)

        for keyword in (title, re.sub(r'^(THE|A)\s+', '', title.strip().upper())):

            if not keyword:
                continue

            for link, name in self._cards(opener, keyword, timeout):
                if clean_title(name) == wanted:
                    return link

        return None

    @staticmethod
    def _sec_code(page):

        '''The download step needs a session code; some episode pages lack one.'''

        try:
            return parseDOM(page, 'input', ret='value', attrs={'id': 'secCode'})[0]
        except IndexError:
            pass

        found = re.findall(
            r'<input[^>]*(?:id="secCode"[^>]*value="([^"]+)"|value="([^"]+)"[^>]*id="secCode")',
            page
        )

        return (found[0][0] or found[0][1]) if found else ''

    @cache_method(cache_duration(440))
    def get(self, query):

        self.list = []
        query, imdb = self._split(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())
            query = re.sub(r'\bS(\d{1,2})\s+E(\d{1,2})\b', r'S\1E\2', query, flags=re.I)

            opener, jar = self._opener()
            timeout = int(control.setting('timeout'))

            # prime session cookies
            self._get(opener, self.base_link, timeout=timeout)

            match = re.findall(r'^(?P<title>.+)[\s+\(|\s+](?P<year>\d{4})', query)

            if len(match) > 0:

                title = match[0][0].strip()

                if imdb.startswith('tt'):
                    cards = self._cards(opener, imdb, timeout)
                    frame = cards[0][0] if cards else self.base_link + 'view/' + imdb
                else:
                    frame = self._match_card(opener, title, timeout)

                    if frame is None:
                        log_debug('Subztv did not provide any results')
                        return

                frames = [frame]

            else:

                tv_match = re.findall(r'^(?P<title>.+)\s+S(\d+)E(\d+)', query, flags=re.I)

                if not tv_match:
                    # a series-only site, so a query without SxxExx cannot match
                    log_debug('Subztv needs an SxxExx query, got: {0}'.format(query))
                    return self.list

                title, season, episode = tv_match[0]

                # must anchor on a digit boundary: "season-1-episode-1" is also a
                # prefix of "season-1-episode-11", which is a different episode
                ep_re = re.compile(
                    r'season-{0}-episode-{1}(?!\d)'.format(int(season), int(episode)), flags=re.I
                )

                # series need two hops: resolve the show page first, then the
                # episode page hanging off it (search cards only link to shows)
                if imdb.startswith('tt'):
                    show = self.base_link + 'view/' + imdb
                else:
                    show = self._match_card(opener, title, timeout)

                    if show is None:
                        log_debug('Subztv did not provide any results')
                        return

                show_page = self._get(opener, show, timeout=timeout)
                show_links = re.findall(r'href="([^"]+)"', show_page)

                # whole-season packs hold every episode of the season in one
                # multi subtitle archive; offer them alongside the episode subs
                pack_re = re.compile(
                    r'season-{0}(?!\d).*?(?:complete[-_]pack|season[-_]pack)'.format(int(season)),
                    flags=re.I
                )

                episode = next(
                    (link for link in show_links
                     if '/view/' in link.lower() and ep_re.search(link)),
                    None
                )

                pack = next(
                    (link for link in show_links
                     if '/view/' in link.lower() and pack_re.search(link)),
                    None
                )

                frames = [f for f in (episode, pack) if f]

                if not frames:
                    log_debug('Subztv did not provide any results')
                    return

            # collect the rows of every page, keeping the frame each came from
            items = []

            for page_url in frames:

                page = self._get(opener, page_url, timeout=timeout)
                page_sec = self._sec_code(page)

                if not page_sec:
                    log_debug('Subztv found no session code for the download step')
                    continue

                tbody = re.search(r'<tbody>([\s\S]*?)</tbody>', page, flags=re.I)

                if not tbody:
                    continue

                for row in re.findall(r'<tr>([\s\S]*?)</tr>', tbody.groups()[0], flags=re.I):
                    items.append((page_url, page_sec, row))

            if not items:
                log_debug('Subztv did not provide any results')
                return

            session = self._cookie(jar, 'PHPSESSID')

        except Cancelled:

            log_debug('Subztv download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Subztv failed at get function, reason: ' + str(e))

            return

        for frame, sec_code, item in items:

            try:

                if 'alt="el"' not in item:
                    continue

                token = re.search(r"downloadMe\('([\w-]+)'", item).groups()[0]

                downloads = re.search(
                    r'</button></td>\s*<td><span[^>]*>([^<]+)</span></td>\s*<td>([^<]+)</td>',
                    item, flags=re.I
                )

                if not downloads:
                    continue

                downloads, name = re.sub('[^0-9]', '', downloads.groups()[0]) or '0', downloads.groups()[1].strip()
                name = replaceHTMLCodes(name)

                dll = self.base_link + 'dll/' + token + '/0/' + sec_code

                # the download step needs the full id segment, e.g. "tt0133093"
                # but also "greekmtdb:season:231393:1"
                try:
                    ref_imdb = re.search(r'/view/([^/]+)/', str(frame)).groups()[0]
                except Exception:
                    ref_imdb = ''

                # session state packed into the url, search and download run isolated
                url = '|'.join([frame, dll, session, quote_plus(name), ref_imdb])

                self.list.append(
                    {
                        'name': name, 'url': url, 'source': 'subztv', 'rating': self._rating(downloads),
                        'title': name, 'downloads': downloads
                    }
                )

            except Exception as e:

                log_debug('Subztv failed at self.list formation function, reason: ' + str(e))

                continue

        return self.list

    def _rating(self, downloads):

        try:

            rating = int(downloads)

        except Exception:

            rating = 0

        if rating < 10:
            rating = 1
        elif 10 <= rating < 20:
            rating = 2
        elif 20 <= rating < 30:
            rating = 3
        elif 30 <= rating < 40:
            rating = 4
        elif rating >= 40:
            rating = 5

        return rating

    def _archive(self, path, sub, data, timeout):

        '''
        GreekSubs.net serves whole-season packs as multi subtitle archives
        (a single zip holding every episode of the season). These honour the
        keep_zips / extract settings; every other provider ignores them.
        '''

        keep = control.setting('keep_zips') == 'true'
        extract = control.setting('extract') == 'true'

        filename = re.sub(r'[\\/:*?"<>|]', '_', sub)

        if not filename.lower().endswith('.zip'):
            filename += '.zip'

        archive = control.join(path, filename)

        with open(archive, 'wb') as subFile:
            subFile.write(data)

        log_debug('Subztv archive received: {0} ({1} bytes)'.format(filename, len(data)))

        if keep and not extract:

            log_debug('Subztv keeping the archive as requested')
            return archive

        zip_file = zipfile.ZipFile(BytesIO(data))
        files = zip_file.namelist()
        subs = [i for i in files if i.lower().endswith(('.srt', '.sub'))]

        if not subs:
            raise Exception('no subtitles inside archive')

        if extract and len(subs) > 1 and keep:
            log_debug('Subztv archive holds {0} subtitles'.format(len(subs)))

        zip_file.extractall(path)

        if len(subs) > 1 and control.setting('extract') == 'true':
            # a pack covers the whole season, so let the user pick the episode
            selected = pick(subs)
        else:
            selected = subs[0]

        return control.join(path, selected)

    def download(self, path, url):

        try:

            frame, dll, session, sub, ref_imdb = url.split('|')
            sub = unquote_plus(sub)
            timeout = int(control.setting('download_timeout'))

            opener, _jar = self._opener()

            headers = {'Referer': frame}
            if session:
                headers['Cookie'] = 'PHPSESSID=' + session

            req = Request(dll)
            req.add_header('User-Agent', self.user_agent)
            for key, value in headers.items():
                req.add_header(key, value)

            init = opener.open(req, timeout=timeout).read().decode('utf-8', errors='replace')

            try:
                imdb = parseDOM(init, 'input', ret='value', attrs={'name': 'uid'})[0]
            except IndexError:
                imdb = ref_imdb

            try:
                sub_name = parseDOM(init, 'input', ret='value', attrs={'name': 'output'})[0]
            except IndexError:
                sub_name = sub + '.srt'

            post = {'langcode': 'el', 'uid': imdb, 'output': sub_name.lower(), 'dll': '1'}

            req = Request(dll, data=urlencode(post).encode('utf-8'))
            req.add_header('User-Agent', self.user_agent)
            req.add_header('Referer', dll)
            req.add_header('Origin', self.base_link.rstrip('/'))
            if session:
                req.add_header('Cookie', 'PHPSESSID=' + session)

            result = opener.open(req, timeout=timeout).read()

            if result[:4] == b'PK\x03\x04':

                return self._archive(path, sub, result, timeout)

            filename = re.sub(r'[\\/:*?"<>|]', '_', sub)
            if not filename.lower().endswith(('.srt', '.sub')):
                filename += '.srt'

            f = control.join(path, filename)

            with open(f, 'wb') as subFile:
                subFile.write(result)

            _dirs, files = control.listDir(path)

            if len(files) == 0:
                return

            return f

        except Cancelled:

            log_debug('Subztv download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Subztv subtitle download failed for the following reason: ' + str(e))

            return
