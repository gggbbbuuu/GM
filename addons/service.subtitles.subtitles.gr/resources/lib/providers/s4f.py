# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Subs4Free / Subs4Series provider, ported from
    service.subtitles.greeksubs by Bugatsinho and rewritten to tulip idioms.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import os
import re
import sys
import traceback
import zipfile
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor, build_opener

from resources.lib.utils.tools import Cancelled, pick, cache_method, cache_duration, randomagent
from resources.lib.utils import impersonate
from tulip import kodi as control
from netclient import Net
from domparsers import parseDOM
from tulip.cleantitle import replaceHTMLCodes
from urllib.parse import quote_plus, quote, unquote_plus, urlencode
from urllib.request import urlopen, Request
from io import BytesIO
from tulip.log import log as log_debug


class S4f:

    def __init__(self):

        self.list = []
        self.base_link = 'https://www.subs4free.club'
        self.base_tv_link = 'https://www.subs4series.com'
        self.search = 'search_report.php?search={0}&searchType=1'
        self.user_agent = 'curl/8.14.1'

    @staticmethod
    def _split(query):

        query = str(query)

        if '/imdb=' in query:
            query, imdb = query.split('/imdb=', 1)
        else:
            imdb = '0'

        return query.strip(), imdb.strip()

    def _series_search(self, keyword, timeout):

        '''
        Series search goes through the TLS-impersonating transport: subs4series
        sits behind Cloudflare (which rejects urllib outright) plus Anubis.
        Returns a list of (url, title, downloads) tuples.
        '''

        sess = impersonate.session(timeout=timeout)

        if sess is None:
            log_debug('S4f series search needs script.module.curlcffi, skipping')
            return []

        url = '/'.join([self.base_tv_link, self.search.format(quote_plus(keyword))])

        try:
            response = sess.get(url, headers={'Referer': self.base_tv_link + '/'}, timeout=timeout)
        except Exception as e:
            log_debug('S4f series search request failed: ' + str(e))
            return []
        finally:
            impersonate.close(sess)

        result = response.text

        if 'not a bot' in result.lower() or 'Attention Required' in result:
            log_debug('S4f series search was challenged despite impersonation')
            return []

        entries = re.findall(
            r'<a href="(/greek-subtitles/[^"]+)"[^>]*title="([^"]+)"', result, flags=re.I
        )

        urls = []

        for href, name in entries:
            try:
                downloads = self._series_downloads(result, href)
            except Exception:
                downloads = '0'

            urls.append(
                (
                    self._absolute(self.base_tv_link, href),
                    re.sub(r'^Greek subtitles for\s+', '', name).strip(),
                    downloads,
                )
            )

        return urls

    @staticmethod
    def _series_downloads(result, href):

        '''Picks the <B>N</B>DLs count belonging to one search row.'''

        index = result.find(href)

        if index < 0:
            return '0'

        window = result[index:index + 2500]
        found = re.findall(r'<B>(\d+)</B>DLs', window, flags=re.I)

        return found[0] if found else '0'

    @cache_method(cache_duration(440))
    def get(self, query, mode=None):

        '''
        mode selects the catalogue: 'movies' for Subs4Free, 'series' for
        Subs4Series. None keeps the old auto behaviour (title plus year means
        movies, SxxExx means series) and exists for anything still calling
        without a mode.
        '''

        self.list = []
        query, _imdb = self._split(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())
            query = re.sub(r'\bS(\d{1,2})\s+E(\d{1,2})\b', r'S\1E\2', query, flags=re.I)

            match = re.findall(r'^(?P<title>.+)[\s+\(|\s+](?P<year>\d{4})', query)

            headers = {'User-Agent': self.user_agent}
            timeout = int(control.setting('timeout'))
            is_series = False

            if mode in (None, 'movies') and len(match) > 0:

                title, year = match[0][0], match[0][1]

                headers['Referer'] = 'https://www.subs4free.info/'

                url = '/'.join([self.base_link, self.search.format(quote_plus('{0} {1}'.format(title, year)))])

                result = Net(user_agent=self.user_agent, timeout=timeout).http_GET(
                    url, headers={'Referer': headers['Referer']}
                ).nodecode(True).content.decode('utf-8', errors='replace')
                result = self._text(result)

                divs = parseDOM(result, 'div', attrs={'class': 'movie-download'})
                divs = [i for i in divs if '/subtitles-in-greek' in i]

                urls = [
                    (
                        parseDOM(i, 'a', ret='href')[0],
                        parseDOM(i, 'a', ret='title')[0],
                        re.findall(r'<b>(\d+)</b>DLs', i, flags=re.I)[0]
                    )
                    for i in divs if i
                ]

                urls = [
                    (self._absolute(self.base_link, i[0]), i[1].split('for ', 1)[1], i[2])
                    for i in urls if i
                ]

            else:

                if mode == 'movies':
                    log_debug('S4f movies needs a title plus year query, got: {0}'.format(query))
                    return self.list

                is_series = True

                tv_match = re.findall(r'^(?P<title>.+)\s+(?P<hdlr>S\d+E\d+)', query, flags=re.I)

                if not tv_match:
                    log_debug('S4f needs an SxxExx query for series, got: {0}'.format(query))
                    return self.list

                title, hdlr = tv_match[0]

                urls = self._series_search(
                    '{0} {1}'.format(title, hdlr), timeout
                )

        except Cancelled:

            log_debug('S4f download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('S4f failed at get function, reason: ' + str(e))

            return

        for i in urls:

            try:

                name = i[1].replace('_', '').replace('%20', '.')
                name = replaceHTMLCodes(name)
                downloads = re.sub('[^0-9]', '', i[2]) or '0'

                self.list.append(
                    {
                        'name': name, 'url': i[0],
                        'source': 's4f_series' if is_series else 's4f',
                        'rating': self._rating(downloads),
                        'title': name, 'downloads': downloads
                    }
                )

            except Cancelled:

                log_debug('S4f download cancelled by user')


                return

            except Exception as e:

                _, __, tb = sys.exc_info()

                traceback.print_tb(tb)

                log_debug('S4f failed at self.list formation function, reason: ' + str(e))

                continue

        return self.list

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

        return base + href if href.startswith('/') else '/'.join([base, href])

    def _rating(self, downloads):

        try:

            rating = int(downloads)

        except Exception:

            rating = 0

        if rating < 100:
            rating = 1
        elif 100 <= rating < 200:
            rating = 2
        elif 200 <= rating < 300:
            rating = 3
        elif 300 <= rating < 400:
            rating = 4
        elif rating >= 400:
            rating = 5

        return rating

    def download(self, path, url):

        try:

            timeout = int(control.setting('download_timeout'))
            is_series = 'subs4series' in url

            jar = CookieJar()
            opener = build_opener(HTTPCookieProcessor(jar))

            if is_series:

                return self._series_download(path, url, timeout)

            else:

                headers = {
                    'User-Agent': self.user_agent, 'Accept': '*/*', 'Referer': url, 'Origin': self.base_link
                }

                page = self._open(opener, url, headers, timeout)
                control.sleep(3000)

                pos = parseDOM(page, 'div', attrs={'class': 'download-btn'})[0]
                pos = parseDOM(pos, 'input', ret='value', attrs={'name': 'id'})[0]

                post_url = self.base_link + '/getSub.php'
                post = {'id': pos, 'x': '107', 'y': '35'}

                surl = self._post_url(opener, post_url, post, headers, timeout)
                data = self._read(opener, surl, headers, timeout)

            filename = unquote_plus(surl.rpartition('/')[2].split('?')[0]) or 'subtitle.zip'
            filename = re.sub(r'[\\/:*?"<>|]', '_', filename)

            return self._extract(path, filename, data, timeout)

        except Cancelled:

            log_debug('S4f download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('S4f subtitle download failed for the following reason: ' + str(e))

            return

    def _series_download(self, path, url, timeout):

        '''
        Series download runs through the TLS-impersonating transport and honours
        a user-supplied session cookie (subs4series rate-limits downloads behind
        a reCAPTCHA, which the user clears in their own browser and hands over
        via the 's4f.session' setting).
        '''

        sess = impersonate.session(
            cookie=control.setting('s4f.session'), timeout=timeout
        )

        if sess is None:
            log_debug('S4f series download needs script.module.curlcffi, skipping')
            return

        try:
            try:
                page = sess.get(url, headers={'Referer': self.base_tv_link + '/'}, timeout=timeout).text
            except Exception as e:
                log_debug('S4f series download page failed: ' + str(e))
                return

            if self._captcha(page):
                log_debug('S4f series download is captcha gated; add a session cookie in settings')
                return

            try:
                pos = re.findall(r'''href=["'](/getSub-.+?)["']''', page, flags=re.I | re.S)[0]
            except IndexError:
                log_debug('S4f series download found no download link')
                return

            post_url = self._absolute(self.base_tv_link, pos)
            referer = url

            try:
                response = sess.get(
                    post_url, headers={'Referer': referer}, timeout=timeout
                )
            except Exception as e:
                log_debug('S4f series download request failed: ' + str(e))
                return

            if self._captcha(response.text):
                log_debug('S4f series download is captcha gated; add a session cookie in settings')
                return

            data = response.content

            if data[:4] != b'PK\x03\x04':
                # maybe a form post is required instead of a plain GET
                form = re.findall(
                    r'<form method="post" action="([^"]+)"[\s\S]{0,900}?</form>', response.text, flags=re.I
                )

                if not form:
                    log_debug('S4f series download returned no archive')
                    return

                try:
                    data = sess.post(
                        self._absolute(self.base_tv_link, form[0]),
                        data={'my_recaptcha_challenge_field': 'manual_challenge'},
                        headers={'Referer': post_url}, timeout=timeout
                    ).content
                except Exception as e:
                    log_debug('S4f series download form post failed: ' + str(e))
                    return

                if data[:4] != b'PK\x03\x04':
                    log_debug('S4f series download returned no archive after form post')
                    return

            filename = unquote_plus(post_url.rpartition('/')[2].split('?')[0]) or 'subtitle.zip'
            filename = re.sub(r'[\\/:*?"<>|]', '_', filename)

            return self._extract(path, filename, data, timeout)
        finally:
            impersonate.close(sess)

    @staticmethod
    def _captcha(html):

        if isinstance(html, bytes):
            html = html.decode('utf-8', errors='replace')

        return 'g-recaptcha' in html or 'not a bot' in html.lower() or 'Attention Required' in html

    def _extract(self, path, filename, data, timeout):

        '''Unpacks an archive, falling back to rar extraction.'''

        if filename.lower().endswith('.rar'):
            return self._save_rar(path, filename, data, timeout)

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

            return self._save_rar(path, filename, data, timeout)

    def _open(self, opener, url, headers, timeout):

        req = Request(url)
        req.add_header('User-Agent', headers.get('User-Agent', randomagent()))

        for key, value in headers.items():
            if key != 'User-Agent':
                req.add_header(key, value)

        response = opener.open(req, timeout=timeout)
        data = response.read()

        try:
            return data.decode('utf-8', errors='replace')
        except Exception:
            return data

    def _read(self, opener, url, headers, timeout):

        req = Request(url)
        req.add_header('User-Agent', headers.get('User-Agent', randomagent()))

        return opener.open(req, timeout=timeout).read()

    def _post_url(self, opener, url, post, headers, timeout):

        req = Request(url, data=urlencode(post).encode('utf-8'))
        req.add_header('User-Agent', headers.get('User-Agent', randomagent()))

        for key, value in headers.items():
            if key != 'User-Agent':
                req.add_header(key, value)

        return opener.open(req, timeout=timeout).geturl()

    def _last_url(self, opener, url, headers, timeout):

        # page was already fetched with _open, just resolve the final url
        req = Request(url)
        req.add_header('User-Agent', headers.get('User-Agent', randomagent()))

        return opener.open(req, timeout=timeout).geturl()

    def _save_rar(self, path, filename, data, _timeout):

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
            log_debug('S4f could not extract subtitle from rar archive')
            return

        filename = pick(filenames)

        return control.join(path, filename)
