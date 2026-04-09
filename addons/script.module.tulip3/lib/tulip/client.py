# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


from __future__ import absolute_import, division, print_function

import os.path

from tulip.cleantitle import replaceHTMLCodes, stripTags
from tulip.parsers import parseDOM, parseDOM2, parse_headers
from tulip.user_agents import CHROME, ANDROID
from tulip.utils import percent
from tulip.net import Net
from tulip import m3u8
import sys, traceback, json, ssl, time
from os.path import basename
try:
    from tulip.log import log_debug
except Exception:
    log_debug = None
try:
    from tulip import control
except Exception:
    control = None


from tulip.compat import (
    urllib2, cookielib, urlparse, URLopener, unquote, str, urlsplit, urlencode, bytes, is_py3, addinfourl, py3_dec,
    iteritems, HTTPError, quote, py2_enc, urlunparse, httplib, Request, urlopen, parse_qsl
)


# noinspection PyUnboundLocalVariable
def request(
        url, close=True, redirect=True, error=False, proxy=None, post=None, headers=None, mobile=False, limit=None,
        referer=None, cookie=None, output='', timeout='30', username=None, password=None, verify=True, as_bytes=False
):

    # This function has been deprecated

    url = py3_dec(url)

    if isinstance(post, dict):
        post = bytes(urlencode(post), encoding='utf-8')
    elif isinstance(post, str) and is_py3:
        post = bytes(post, encoding='utf-8')

    try:

        handlers = []

        if username is not None and password is not None and not proxy:

            passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passmgr.add_password(None, uri=url, user=username, passwd=password)
            handlers += [urllib2.HTTPBasicAuthHandler(passmgr)]
            opener = urllib2.build_opener(*handlers)
            urllib2.install_opener(opener)

        if proxy is not None:

            if username is not None and password is not None:

                if is_py3:

                    passmgr = urllib2.HTTPPasswordMgr()
                    passmgr.add_password(None, uri=url, user=username, passwd=password)

                else:

                    passmgr = urllib2.ProxyBasicAuthHandler()
                    passmgr.add_password(None, uri=url, user=username, passwd=password)

                handlers += [
                    urllib2.ProxyHandler({'http': '{0}'.format(proxy)}), urllib2.HTTPHandler,
                    urllib2.ProxyBasicAuthHandler(passmgr)
                ]

            else:

                handlers += [urllib2.ProxyHandler({'http':'{0}'.format(proxy)}), urllib2.HTTPHandler]

            opener = urllib2.build_opener(*handlers)
            urllib2.install_opener(opener)

        if output == 'cookie' or output == 'extended' or close is not True:

            cookies = cookielib.LWPCookieJar()
            handlers += [urllib2.HTTPHandler(), urllib2.HTTPSHandler(), urllib2.HTTPCookieProcessor(cookies)]

            opener = urllib2.build_opener(*handlers)
            urllib2.install_opener(opener)

        if not verify or ((2, 7, 8) < sys.version_info < (2, 7, 12)):

            try:

                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                handlers += [urllib2.HTTPSHandler(context=ssl_context)]
                opener = urllib2.build_opener(*handlers)
                urllib2.install_opener(opener)

            except Exception:

                pass

        try:
            headers.update(headers)
        except Exception:
            headers = {}

        if 'User-Agent' in headers:
            pass
        elif mobile is not True:
            headers['User-Agent'] = CHROME
        else:
            headers['User-Agent'] = ANDROID

        if 'Referer' in headers:
            pass
        elif referer is None:
            headers['Referer'] = '%s://%s/' % (urlparse(url).scheme, urlparse(url).netloc)
        else:
            headers['Referer'] = referer

        if not 'Accept-Language' in headers:
            headers['Accept-Language'] = 'en-US'

        if 'Cookie' in headers:
            pass
        elif cookie is not None:
            headers['Cookie'] = cookie

        if redirect is False:

            class NoRedirectHandler(urllib2.HTTPRedirectHandler):

                def http_error_302(self, reqst, fp, code, msg, head):

                    infourl = addinfourl(fp, head, reqst.get_full_url())
                    infourl.status = code
                    infourl.code = code

                    return infourl

                http_error_300 = http_error_302
                http_error_301 = http_error_302
                http_error_303 = http_error_302
                http_error_307 = http_error_302

            opener = urllib2.build_opener(NoRedirectHandler())
            urllib2.install_opener(opener)

            try:
                del headers['Referer']
            except Exception:
                pass

        req = Request(url, data=post, headers=headers)

        try:

            response = urllib2.urlopen(req, timeout=int(timeout))

        except HTTPError as response:

            if response.code == 503:

                if 'cf-browser-verification' in response.read(5242880):

                    if log_debug:
                        log_debug('This request cannot be handled due to human verification gate')
                    else:
                        print('This request cannot be handled due to human verification gate')

                    return

                elif error is False:
                    return

            elif error is False:
                return

        if output == 'cookie':

            try:
                result = '; '.join(['{0}={1}'.format(i.name, i.value) for i in cookies])
            except Exception:
                pass

        elif output == 'response':

            if limit == '0':
                result = (str(response.code), response.read(224 * 1024))
            elif limit is not None:
                result = (str(response.code), response.read(int(limit) * 1024))
            else:
                result = (str(response.code), response.read(5242880))

        elif output == 'chunk':

            try:
                content = int(response.headers['Content-Length'])
            except Exception:
                content = (2049 * 1024)

            if content < (2048 * 1024):
                return
            result = response.read(16 * 1024)

        elif output == 'extended':

            try:
                cookie = '; '.join(['%s=%s' % (i.name, i.value) for i in cookies])
            except Exception:
                pass

            content = response.headers
            result = response.read(5242880)

            if not as_bytes:

                result = py3_dec(result)

            return result, headers, content, cookie

        elif output == 'geturl':

            result = response.geturl()

        elif output == 'headers':

            content = response.headers

            if close:
                response.close()

            return content

        elif output == 'file_size':

            try:
                content = int(response.headers['Content-Length'])
            except Exception:
                content = '0'

            response.close()

            return content

        elif output == 'json':

            content = json.loads(response.read(5242880))

            response.close()

            return content

        else:

            if limit == '0':
                result = response.read(224 * 1024)
            elif limit is not None:
                if isinstance(limit, int):
                    result = response.read(limit * 1024)
                else:
                    result = response.read(int(limit) * 1024)
            else:
                result = response.read(5242880)

        if close is True:
            response.close()

        if not as_bytes:
            result = py3_dec(result)

        return result

    except Exception as reason:

        _, __, tb = sys.exc_info()

        print(traceback.print_tb(tb))
        if log_debug:
            log_debug('Request failed, reason: ' + repr(reason) + ' on url: ' + url)
        else:
            print('Request failed, reason: ' + repr(reason) + ' on url: ' + url)

        return


def retriever(source, destination, user_agent=None, referer=None, reporthook=None, data=None, **kwargs):

    if user_agent is None:
        user_agent = CHROME

    if referer is None:
        referer = '{0}://{1}/'.format(urlparse(source).scheme, urlparse(source).netloc)

    class Opener(URLopener):

        version = user_agent

        def __init__(self, **x509):

            URLopener.__init__(self)

            super(Opener, self).__init__(**x509)
            headers = [('User-Agent', self.version), ('Accept', '*/*'), ('Referer', referer)]

            if kwargs:
                headers.extend(iteritems(kwargs))

            self.addheaders = headers

    Opener().retrieve(source, destination, reporthook, data)


def url2name(url):

    url = url.split('|')[0]
    return basename(unquote(urlsplit(url)[2]))


def download_media(
        url, output_folder, filename=None, heading=control.name(),
        line1='Downloading...[CR]%.02f MB of %.02f MB[CR]Speed: %.02f Kb/s'
):

    with control.ProgressDialog(heading, line1=line1) as pd:

        user_agent = CHROME

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if not filename:
            filename = url2name(url)
        elif not filename.endswith(('.mp4', '.mkv', '.flv', '.avi', '.mpg', '.m4v')):
            filename += '.mp4'

        destination = os.path.join(output_folder, filename)

        if '|' in url:
            url, _, head = url.rpartition('|')
            headers = dict(parse_qsl(head))
            user_agent = headers['User-Agent']
            if 'Referer' in headers:
                referer = headers['Referer']
            else:
                referer = '{0}://{1}/'.format(urlparse(url).scheme, urlparse(url).netloc)
        else:
            referer = '{0}://{1}/'.format(urlparse(url).scheme, urlparse(url).netloc)

        start_time = time.time()

        try:
            retriever(
                url, destination, user_agent=user_agent, referer=referer,
                reporthook=lambda numblocks, blocksize, filesize: _pbhook(
                    numblocks, blocksize, filesize, pd, start_time, line1
                )
            )
        except Exception:
            pd.update(100, 'Cancelled')


def _pbhook(numblocks, blocksize, filesize, pd, start_time, line1):

    _percent = min(numblocks * blocksize * 100 / filesize, 100)
    if is_py3:
        _percent = int(_percent)
    currently_downloaded = float(numblocks) * blocksize / (1024 * 1024)
    kbps_speed = numblocks * blocksize / (time.time() - start_time)

    if kbps_speed > 0:
        eta = (filesize - numblocks * blocksize) / kbps_speed
    else:
        eta = 0

    kbps_speed = kbps_speed / 1024
    total = float(filesize) / (1024 * 1024)
    line1 = line1 % (currently_downloaded, total, kbps_speed)
    line1 += ' - ETA: %02d:%02d' % divmod(eta, 60)
    pd.update(_percent, line1)

    if pd.is_canceled():
        raise Exception


class M3U8:

    def __init__(self, url, headers=None, heading=''):

        self.url = url
        self.headers = headers
        self.heading = heading

    def stream_picker(self, qualities, urls):

        if not self.heading:
            heading = 'Select a quality'
        elif isinstance(self.heading, int) and control:
            heading = control.lang(self.heading)
        else:
            heading = self.heading

        _choice = control.selectDialog(heading=heading, list=qualities)

        if _choice <= len(qualities) and not _choice == -1:
            self.url = urls[_choice]
            return self.url

    def m3u8_picker(self):

        try:

            if '|' not in self.url or self.headers is None:
                raise TypeError

            if '|' in self.url:

                link, _, head = self.url.rpartition('|')
                headers = dict(parse_qsl(head))
                streams = m3u8.load(link, headers=headers).playlists

            else:

                streams = m3u8.load(self.url, headers=self.headers).playlists

        except TypeError:

            streams = m3u8.load(self.url).playlists

        if not streams:
            return self.url

        qualities = []
        urls = []

        for stream in streams:

            quality = repr(stream.stream_info.resolution).strip('()').replace(', ', 'x')

            if quality == 'None':
                quality = 'Auto'

            uri = stream.absolute_uri

            qualities.append(quality)

            try:

                if '|' not in self.url:
                    raise TypeError

                urls.append(uri + ''.join(self.url.rpartition('|')[1:]))

            except TypeError:
                urls.append(uri)

        if len(qualities) == 1:

            return self.url

        else:

            return self.stream_picker(qualities, urls)

    def downloader(self, output_folder, filename=None, heading='', line1='', pd_dialog='Downloading segment {0} from {1}'):

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if not heading:
            heading = 'Downloading ts segments'
        elif isinstance(heading, int) and control:
            heading = control.lang(self.heading)

        url = self.m3u8_picker()

        if '|' in url:

            url, _, head = url.rpartition('|')
            headers = dict(parse_qsl(head))

        elif self.headers:

            headers = self.headers

        else:

            headers = {'User-Agent': CHROME}

        _m3u8 = m3u8.load(url, headers=headers)

        segments = _m3u8.files

        if not filename:
            filename = os.path.split(urlparse(url).path.replace('m3u8', 'ts'))[1]
        elif not filename.endswith('.ts'):
            filename += '.ts'

        destination = os.path.join(output_folder, filename)

        if os.path.exists(destination):
            pass

        f = open(destination,  'ab')

        with control.ProgressDialog(heading=heading, line1=line1) as pd:

            for count, segment in list(enumerate(segments, start=1)):

                if not segment.startswith('http'):
                    segment = ''.join([_m3u8.base_uri, segment])

                req = Request(segment)

                for k, v in iteritems(headers):
                    req.add_header(k, v)

                opener = urlopen(req)
                data = opener.read()
                f.write(data)

                pd.update(percent=percent(count, len(segments)), line1=pd_dialog.format(count, len(segments)))

                if pd.is_canceled():
                    f.close()
                    break

            f.close()


def parseJSString(s):
    try:
        offset = 1 if s[0] == '+' else 0
        val = int(eval(s.replace('!+[]', '1').replace('!![]', '1').replace('[]','0').replace('(', 'str(')[offset:]))
        return val
    except Exception:
        pass


def quote_paths(url):

    """
    This function will quote paths **only** in a given url
    :param url: string or unicode
    :return: joined url string
    """

    try:

        url = py2_enc(url)

        if url.startswith('http'):

            parsed = urlparse(url)
            processed_path = '/'.join([quote(i) for i in parsed.path.split('/')])
            url = urlunparse(parsed._replace(path=processed_path))

            return url

        else:

            path = '/'.join([quote(i) for i in url.split('/')])
            return path

    except Exception:

        return url


def check_connection(url="1.1.1.1", timeout=3):

    conn = httplib.HTTPConnection(url, timeout=timeout)

    try:

        conn.request("HEAD", "/")
        conn.close()

        return True

    except Exception as e:

        if log_debug:
            log_debug(e)
        else:
            print(e)

        return False


__all__ = [
    'parseDOM', 'request', 'stripTags', 'retriever', 'replaceHTMLCodes', 'parseJSString', 'parse_headers',
    'url2name', 'check_connection', 'parseDOM2', 'quote_paths', 'Net', 'M3U8'
]
