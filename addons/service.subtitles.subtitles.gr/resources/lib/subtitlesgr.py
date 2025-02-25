# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import print_function

from contextlib import closing
from os.path import basename, split as os_split
from resources.lib.tools import multichoice, cache_method, cache_duration
import zipfile, re, sys, traceback
from tulip import control, client
from tulip.log import log_debug
from tulip.user_agents import randomagent
from tulip.compat import unquote_plus, quote_plus, urlopen, quote, BytesIO, py3_dec, Request


class Subtitlesgr:

    def __init__(self):

        self.list = []
        self.base_link = 'http://gr.greek-subtitles.com'
        self.download_link = 'http://www.greeksubtitles.info'

    @cache_method(cache_duration(440))
    def get(self, query):

        query = py3_dec(query)

        try:

            query = ' '.join(unquote_plus(re.sub(r'%\w\w', ' ', quote_plus(query))).split())

            url = ''.join([self.base_link, '/search.php?name={0}'.format(quote_plus(query))])

            result = client.request(url, timeout=control.setting('timeout'))

            try:
                result = result.decode('utf-8', errors='replace')
            except AttributeError:
                pass

            items = client.parseDOM(result, 'tr', attrs={'on.+?': '.+?'})

            if not items:
                log_debug('Subtitles.gr did not provide any results')
                return

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Subtitles.gr failed at get function, reason: ' + str(e))

            return

        for item in items:

            try:

                if u'flags/el.gif' not in item:

                    continue

                try:
                    uploader = client.parseDOM(item, 'a', attrs={'class': 'link_from'})[0].strip()
                    uploader = client.replaceHTMLCodes(uploader)
                except IndexError:
                    uploader = ''

                try:
                    uploader = uploader.decode('utf-8')
                except AttributeError:
                    pass

                if not uploader:
                    uploader = 'other'

                try:
                    downloads = client.parseDOM(item, 'td', attrs={'class': 'latest_downloads'})[0].strip()
                except:
                    downloads = '0'

                downloads = re.sub('[^0-9]', '', downloads)

                name = client.parseDOM(item, 'a', attrs={'onclick': 'runme.+?'})[0]
                name = ' '.join(re.sub('<.+?>', '', name).split())
                name = client.replaceHTMLCodes(name)
                label = u'[{0}] {1} [{2} DLs]'.format(uploader, name, downloads)

                url = client.parseDOM(item, 'a', ret='href', attrs={'onclick': 'runme.+?'})[0]
                url = url.split('"')[0].split('\'')[0].split(' ')[0]
                url = client.replaceHTMLCodes(url)
                url = url.encode('utf-8')

                rating = self._rating(downloads)

                self.list.append(
                    {
                        'name': label, 'url': url, 'source': 'subtitlesgr', 'rating': rating, 'title': name,
                        'downloads': downloads
                    }
                )

            except Exception as e:

                _, __, tb = sys.exc_info()

                print(traceback.print_tb(tb))

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
            url = client.request(url, output='geturl', timeout=control.setting('timeout'))

            req = Request(url)
            req.add_header('User-Agent', randomagent())
            opener = urlopen(req)
            data = opener.read()
            zip_file = zipfile.ZipFile(BytesIO(data))
            opener.close()
            files = zip_file.namelist()
            files = [i for i in files if i.startswith('subs/')]

            srt = [i for i in files if i.endswith(('.srt', '.sub'))]
            archive = [i for i in files if i.endswith(('.rar', '.zip'))]

            if len(srt) > 0:

                if len(srt) > 1:
                    srt = multichoice(srt)
                else:
                    srt = srt[0]

                result = zip_file.open(srt).read()

                subtitle = basename(srt)

                try:
                    subtitle = control.join(path, subtitle.decode('utf-8'))
                except Exception:
                    subtitle = control.join(path, subtitle)

                with open(subtitle, 'wb') as subFile:
                    subFile.write(result)

                return subtitle

            elif len(archive) > 0:

                if len(archive) > 1:
                    archive = multichoice(archive)
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

                filename = multichoice(filenames)

                try:

                    filename = filename.decode('utf-8')

                except Exception:

                    pass

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

        except Exception as e:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))

            log_debug('Subtitles.gr subtitle download failed for the following reason: ' + str(e))

            return
