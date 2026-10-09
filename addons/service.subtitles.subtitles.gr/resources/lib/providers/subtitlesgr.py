# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from contextlib import closing
from os.path import basename, split as os_split
from resources.lib.utils.tools import Cancelled, pick, cache_method, cache_duration, randomagent
import zipfile, re, sys, traceback
from tulip import kodi as control
from netclient import Net
from domparsers import parseDOM
from tulip.cleantitle import replaceHTMLCodes
from tulip.log import log as log_debug
from urllib.parse import unquote_plus, quote_plus, quote
from urllib.request import urlopen, Request
from io import BytesIO


class Subtitlesgr:

    def __init__(self):

        self.list = []
        self.base_link = 'http://gr.greek-subtitles.com'
        self.download_link = 'http://www.greeksubtitles.info'

    @cache_method(cache_duration(440))
    def get(self, query):

        query = str(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())

            url = ''.join([self.base_link, '/search.php?name={0}'.format(quote_plus(query))])

            result = Net(user_agent=randomagent(), timeout=int(control.setting('timeout'))).http_GET(
                url
            ).nodecode(True).content.decode('utf-8', errors='replace')

            if isinstance(result, bytes):
                result = result.decode('utf-8', errors='replace')

            items = parseDOM(result, 'tr', attrs={'on.+?': '.+?'})

            if not items:
                log_debug('Subtitles.gr did not provide any results')
                return

        except Cancelled:

            log_debug('Subtitlesgr download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Subtitles.gr failed at get function, reason: ' + str(e))

            return

        for item in items:

            try:

                if u'flags/el.gif' not in item:

                    continue

                try:
                    uploader = parseDOM(item, 'a', attrs={'class': 'link_from'})[0].strip()
                    uploader = replaceHTMLCodes(uploader)
                except IndexError:
                    uploader = ''

                uploader = replaceHTMLCodes(uploader)

                if not uploader:
                    uploader = 'other'

                try:
                    downloads = parseDOM(item, 'td', attrs={'class': 'latest_downloads'})[0].strip()
                except:
                    downloads = '0'

                downloads = re.sub('[^0-9]', '', downloads)

                name = parseDOM(item, 'a', attrs={'onclick': 'runme.+?'})[0]
                name = ' '.join(re.sub('<.+?>', '', name).split())
                name = replaceHTMLCodes(name)
                label = u'[{0}] {1} [{2} DLs]'.format(uploader, name, downloads)

                url = parseDOM(item, 'a', ret='href', attrs={'onclick': 'runme.+?'})[0]
                url = url.split('"')[0].split('\'')[0].split(' ')[0]
                url = replaceHTMLCodes(url)

                rating = self._rating(downloads)

                self.list.append(
                    {
                        'name': label, 'url': url, 'source': 'subtitlesgr', 'rating': rating, 'title': name,
                        'downloads': downloads
                    }
                )

            except Cancelled:

                log_debug('Subtitlesgr download cancelled by user')


                return

            except Exception as e:

                _, __, tb = sys.exc_info()

                traceback.print_tb(tb)

                log_debug('Subtitles.gr failed at self.list formation function, reason: ' + str(e))

                return

        return self.list

    def _rating(self, downloads):

        try:

            rating = int(downloads)

        except:

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

            url = re.findall(r'/(\d+)/', url + '/', re.I)[-1]
            url = ''.join([self.download_link, '/getp.php?id={0}'.format(url)])

            url = Net(user_agent=randomagent(), timeout=int(control.setting('download_timeout'))).http_GET(
                url
            ).get_url()

            req = Request(url)
            req.add_header('User-Agent', randomagent())
            opener = urlopen(req, timeout=int(control.setting('download_timeout')))
            data = opener.read()
            zip_file = zipfile.ZipFile(BytesIO(data))
            opener.close()
            files = zip_file.namelist()
            files = [i for i in files if i.startswith('subs/')]

            srt = [i for i in files if i.endswith(('.srt', '.sub'))]
            archive = [i for i in files if i.endswith(('.rar', '.zip'))]

            if len(srt) > 0:

                if len(srt) > 1:
                    srt = pick(srt)
                else:
                    srt = srt[0]

                result = zip_file.open(srt).read()

                subtitle = basename(srt)
                subtitle = control.join(path, subtitle)

                with open(subtitle, 'wb') as subFile:
                    subFile.write(result)

                return subtitle

            elif len(archive) > 0:

                if len(archive) > 1:
                    archive = pick(archive)
                else:
                    archive = archive[0]

                result = zip_file.open(archive).read()

                f = control.join(path, os_split(url)[1])

                with open(f, 'wb') as subFile:
                    subFile.write(result)

                dirs, files = control.listDir(path)

                if len(files) == 0:
                    return

                if zipfile.is_zipfile(f):

                    zipped = zipfile.ZipFile(f)
                    zipped.extractall(path)

                if not zipfile.is_zipfile(f):

                    if control.infoLabel('System.Platform.Windows'):
                        uri = "rar://{0}/".format(quote(f))
                    else:
                        uri = "rar://{0}/".format(quote_plus(f))

                    dirs, files = control.listDir(uri)

                else:

                    dirs, files = control.listDir(path)

                if dirs and not zipfile.is_zipfile(f):

                    for dir in dirs:

                        _dirs, _files = control.listDir(control.join(uri, dir))

                        [files.append(control.join(dir, i)) for i in _files]

                        if _dirs:

                            for _dir in _dirs:

                                _dir = control.join(_dir, dir)

                                __dirs, __files = control.listDir(
                                    control.join(uri, _dir)
                                )

                                [files.append(control.join(_dir, i)) for i in __files]

                filenames = [i for i in files if i.endswith(('.srt', '.sub'))]

                filename = pick(filenames)

                if not control.exists(control.join(path, os_split(filename)[0])) and not zipfile.is_zipfile(f):
                    control.makeFiles(control.join(path, os_split(filename)[0]))

                subtitle = control.join(path, filename)

                if not zipfile.is_zipfile(f):

                    with closing(control.openFile(uri + filename)) as fn:

                        try:
                            output = bytes(fn.readBytes())
                        except Exception:
                            output = bytes(fn.read())

                    content = output.decode('utf-16')

                    with closing(control.openFile(subtitle, 'w')) as subFile:
                        subFile.write(bytearray(content.encode('utf-8')))

                fileparts = os_split(subtitle)[1].split('.')
                # noinspection PyTypeChecker
                result = control.join(os_split(subtitle)[0], 'subtitles.' + fileparts[len(fileparts)-1])

                control.rename(subtitle, result)

                return result

        except Cancelled:

            log_debug('Subtitlesgr download cancelled by user')


            return

        except Exception as e:

            _, __, tb = sys.exc_info()

            traceback.print_tb(tb)

            log_debug('Subtitles.gr subtitle download failed for the following reason: ' + str(e))

            return
