# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


from __future__ import absolute_import, division, print_function

from tulip.cleantitle import replaceHTMLCodes, stripTags
from tulip.parsers import parseDOM, parseDOM2, parse_headers
from tulip.user_agents import CHROME, ANDROID
from tulip.utils import enum
from tulip.net import Net
import sys, traceback, json, ssl
from os import sep
from os.path import basename, splitext
try:
    from tulip.log import log_debug
except Exception:
    log_debug = None


from tulip.compat import (
    urllib2, cookielib, urlparse, URLopener, unquote, str, urlsplit, urlencode, bytes, is_py3, addinfourl, py3_dec,
    iteritems, HTTPError, quote, py2_enc, urlunparse, httplib
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

        req = urllib2.Request(url, data=post, headers=headers)

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


def get_extension(url, response):

    filename = url2name(url)
    if 'Content-Disposition' in response.info():
        cd_list = response.info()['Content-Disposition'].split('filename=')
        if len(cd_list) > 1:
            filename = cd_list[-1]
            if filename[0] == '"' or filename[0] == "'":
                filename = filename[1:-1]
    elif response.url != url:
        filename = url2name(response.url)
    ext = splitext(filename)[1][1:]
    if not ext:
        ext = 'mp4'
    return ext


# noinspection PyUnresolvedReferences
def download_media(url, path, file_name, initiate_int='', completion_int='', exception_int='', progress=None):

    PROGRESS = enum(OFF=0, WINDOW=1, BACKGROUND=2)

    try:
        if progress is None:
            progress = int(control.setting('progress_dialog'))

        active = not progress == PROGRESS.OFF
        background = progress == PROGRESS.BACKGROUND

        if isinstance(initiate_int, int):
            line1 = control.lang(initiate_int).format(file_name)
        else:
            line1 = 'Downloading {0}'.format(file_name)

        with control.ProgressDialog(control.addonInfo('name'), line1, background=background, active=active) as pd:

            try:
                headers = dict([item.split('=') for item in (url.split('|')[1]).split('&')])
                for key in headers:
                    headers[key] = unquote(headers[key])
            except:
                headers = {}

            if 'User-Agent' not in headers:
                headers['User-Agent'] = CHROME

            request = urllib2.Request(url.split('|')[0], headers=headers)
            response = urllib2.urlopen(request)

            if 'Content-Length' in response.info():
                content_length = int(response.info()['Content-Length'])
            else:
                content_length = 0

            file_name += '.' + get_extension(url, response)
            full_path = control.join(path, file_name)
            if log_debug:
                log_debug('Downloading: %s -> %s' % (url, full_path))
            else:
                print('Downloading: %s -> %s' % (url, full_path))

            path = control.transPath(control.legalfilename(path))

            try:
                control.makeFiles(path)
            except Exception as e:
                if log_debug:
                    log_debug('Path Create Failed: %s (%s)' % (e, path))
                else:
                    print('Path Create Failed: %s (%s)' % (e, path))

            if not path.endswith(sep):
                path += sep
            if not control.exists(path):
                raise Exception('Failed to create dir')

            file_desc = control.openFile(full_path, 'w')
            total_len = 0
            cancel = False
            while 1:
                data = response.read(512 * 1024)
                if not data:
                    break

                if pd.is_canceled():
                    cancel = True
                    break

                total_len += len(data)
                if not file_desc.write(data):
                    raise Exception('Failed to write file')

                percent_progress = total_len * 100 / content_length if content_length > 0 else 0
                if log_debug:
                    log_debug('Position : {0} / {1} = {2}%'.format(total_len, content_length, percent_progress))
                else:
                    print('Position : {0} / {1} = {2}%'.format(total_len, content_length, percent_progress))
                pd.update(percent_progress)

            file_desc.close()

        if not cancel:

            if isinstance(completion_int, int):
                control.infoDialog(control.lang(completion_int).format(file_name))
            else:
                control.infoDialog('Download_complete for file name {0}'.format(file_name))

            if log_debug:
                log_debug('Download Complete: {0} -> {1}'.format(url, full_path))
            else:
                print('Download Complete: {0} -> {1}'.format(url, full_path))

    except Exception as e:

        if log_debug:
            log_debug('Error ({0}) during download: {1} -> {2}'.format(str(e), url, file_name))
        else:
            print('Error ({0}) during download: {1} -> {2}'.format(str(e), url, file_name))
        if isinstance(exception_int, int):
            control.infoDialog(control.lang(exception_int).format(str(e), file_name))
        else:
            control.infoDialog('Download_complete for file name {0}'.format(file_name))


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
    'url2name', 'get_extension', 'check_connection', 'parseDOM2', 'quote_paths', 'Net'
]
