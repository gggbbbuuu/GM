# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    TVsubtitles.net (Greek mirror) provider. TV series only.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import sys
import traceback
import zipfile

from resources.lib.utils.tools import Cancelled, pick, cache_method, cache_duration, randomagent, clean_title
from tulip import kodi as control
from netclient import Net
from tulip.cleantitle import replaceHTMLCodes
from urllib.parse import quote as urlquote, quote_plus, unquote_plus
from urllib.request import urlopen, Request
from tulip.log import log as log_debug
from io import BytesIO


class Tvsubs:

    def __init__(self):

        self.list = []
        self.base_link = 'https://gr.tvsubtitles.net/'
        self.index_link = self.base_link + 'tvshows.html'
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

    @cache_method(cache_duration(2880))
    def _index(self):

        result = Net(user_agent=self.user_agent, timeout=int(control.setting('timeout'))).http_GET(
            self.index_link
        ).nodecode(True).content.decode('utf-8', errors='replace')

        if isinstance(result, bytes):
            result = result.decode('utf-8', errors='replace')

        shows = re.findall(
            r'<a href="tvshow-(\d+)-\d+\.html"><b>([^<]+)</b></a>', result, flags=re.I
        )

        seen, index = set(), []

        for show_id, name in shows:
            if show_id not in seen:
                seen.add(show_id)
                index.append((show_id, replaceHTMLCodes(name)))

        return index

    @cache_method(cache_duration(440))
    def get(self, query):

        self.list = []
        query = self._split(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())
            query = re.sub(r'\bS(\d{1,2})\s+E(\d{1,2})\b', r'S\1E\2', query, flags=re.I)
            timeout = int(control.setting('timeout'))
            net = Net(user_agent=self.user_agent, timeout=timeout)

            try:
                title, season, episode = re.findall(r'^(?P<title>.+)\s+S(\d+)E(\d+)', query, flags=re.I)[0]
            except IndexError:
                log_debug('Tvsubs offers subtitles for tv shows only')
                return self.list

            show_id = next(
                (i[0] for i in self._index() if clean_title(i[1]) == clean_title(title)),
                None
            )

            if show_id is None:
                log_debug('Tvsubs did not provide any results')
                return self.list

            season_page = net.http_GET(
                '{0}tvshow-{1}-{2}.html'.format(self.base_link, show_id, int(season))
            ).nodecode(True).content.decode('utf-8', errors='replace')

            key = '{0}x{1:02d}'.format(int(season), int(episode))

            try:
                episode_page = re.search(
                    r'<td>' + re.escape(key) + r'</td>\s*<td[^>]*>\s*<a href="(episode-\d+\.html)">',
                    season_page, flags=re.I
                ).groups()[0]
            except (AttributeError, IndexError):
                log_debug('Tvsubs did not provide any results')
                return self.list

            episode_page = net.http_GET(
                self.base_link + episode_page
            ).nodecode(True).content.decode('utf-8', errors='replace')

            blocks = re.findall(
                r'<a href="/(subtitle-\d+\.html)">([\s\S]*?)</a>', episode_page, flags=re.I
            )
            blocks = [(href, body) for href, body in blocks if 'flags/gr.gif' in body]

            if not blocks:
                log_debug('Tvsubs did not provide any results')
                return self.list

        except Cancelled:

            log_debug('Tvsubs download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Tvsubs failed at get function, reason: ' + str(e))

            return

        for href, block in blocks:

            try:

                name = re.search(r'<h5[^>]*>([\s\S]*?)</h5>', block, flags=re.I).groups()[0]
                name = re.sub(r'<.+?>', '', name).strip()
                name = replaceHTMLCodes(name)

                try:
                    downloads = re.search(r'downloads\.png[^>]*>\s*(\d+)', block, flags=re.I).groups()[0]
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
                        'name': name, 'url': self.base_link + href, 'source': 'tvsubs',
                        'rating': rating, 'title': name, 'downloads': downloads
                    }
                )

            except Exception as e:

                log_debug('Tvsubs failed at self.list formation function, reason: ' + str(e))

                continue

        return self.list

    def download(self, path, url):

        try:

            timeout = int(control.setting('download_timeout'))
            net = Net(user_agent=self.user_agent, timeout=timeout)

            page = net.http_GET(
                url, headers={'Referer': url}
            ).nodecode(True).content.decode('utf-8', errors='replace')

            wait_id = re.search(r'href="(download-\d+\.html)"', page, flags=re.I).groups()[0]
            wait_url = self.base_link + wait_id

            raw = net.http_GET(
                wait_url, headers={'Referer': url}
            ).nodecode(True).content

            if isinstance(raw, bytes) and raw[:2] == b'\x1f\x8b':
                # payload arrived still compressed, decompress manually
                import gzip

                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass

            data = None

            if isinstance(raw, bytes) and raw[:4] == b'PK\x03\x04':
                # file served directly without timer page
                log_debug('Tvsubs file served directly without timer')
                data = raw
                filename = wait_id.replace('.html', '.zip')
            else:
                wait = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw

                parts = re.findall(r"var s(\d+)\s*=\s*['\"]([^'\"]*)['\"]", wait, flags=re.I)
                parts = [p[1] for p in sorted(parts, key=lambda p: int(p[0]))]

                if not parts:
                    title = re.search(
                        r'<title[^>]*>([^<]{0,120})', wait, flags=re.I
                    )
                    log_debug(
                        'Tvsubs wait page gave no download link (length {0}, title {1!r}, timer {2})'.format(
                            len(wait), title.groups()[0] if title else None, 'linkPlace' in wait
                        )
                    )
                    raise Exception('download link not found')

                data_url = self.base_link + urlquote(''.join(parts), safe=':/')

                req = Request(data_url)
                req.add_header('User-Agent', randomagent())
                req.add_header('Referer', wait_url)

                data = urlopen(req, timeout=timeout).read()

                filename = unquote_plus(data_url.rpartition('/')[2].split('?')[0]) or 'subtitle.zip'

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
                    log_debug('Tvsubs could not extract subtitle from archive')
                    return

                subtitle = pick(filenames)
                control.deleteFile(f)

                return control.join(path, subtitle)

        except Cancelled:

            log_debug('Tvsubs download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Tvsubs subtitle download failed for the following reason: ' + str(e))

            return
