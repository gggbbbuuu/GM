# -*- coding: utf-8 -*-

import re
import sys
import gzip
import random
import time

import requests

import simplejson as json
import six
from six.moves import range as x_range

from resources.lib.modules import control
from resources.lib.modules import dom_parser
from resources.lib.modules import log_utils

try: # Py2
    from urlparse import urlparse, urljoin
    from urllib import quote, urlencode, quote_plus, addinfourl
    import cookielib
    import urllib2
    from cStringIO import StringIO
    from HTMLParser import HTMLParser
    unescape = HTMLParser().unescape
    HTTPError = urllib2.HTTPError
except ImportError: # Py3:
    from http import cookiejar as cookielib
    from html import unescape
    import urllib.request as urllib2
    from io import StringIO
    from urllib.parse import urlparse, urljoin, quote, urlencode, quote_plus
    from urllib.response import addinfourl
    from urllib.error import HTTPError
finally:
    urlopen = urllib2.urlopen
    Request = urllib2.Request

if six.PY2:
    _str = str
    str = unicode
    unicode = unicode
    basestring = basestring
    def bytes(b, encoding="ascii"):
        return _str(b)
elif six.PY3:
    bytes = bytes
    str = unicode = basestring = str


UserAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
MobileUserAgent = 'Mozilla/5.0 (Android 10; Mobile; rv:83.0) Gecko/83.0 Firefox/83.0'

dnt_headers = {
    'User-Agent': UserAgent,
    'Accept': '*/*',
    'Accept-Encoding': 'identity;q=1, *;q=0',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'DNT': '1'
}

regex_pattern1 = r'(?:iframe|source).+?(?:src)=(?:\"|\')(.+?)(?:\"|\')'
regex_pattern2 = r'(?:data-video|data-src|data-href)=(?:\"|\')(.+?)(?:\"|\')'
regex_pattern3 = r'(?:file|source)(?:\:)\s*(?:\"|\')(.+?)(?:\"|\')'
regex_pattern4 = r'''(magnet:\?[^"']+)'''
regex_pattern5 = r'<[iI][fF][rR][aA][mM][eE].+?[sS][rR][cC]="(.+?)"'
regex_pattern6 = r'''['"]file['"]\s*:\s*['"]([^'"]+)'''
regex_pattern7 = r'''['"]?file['"]?\s*:\s*['"]([^'"]*)'''
regex_pattern8 = r'file(?:\'|\")?\s*(?:\:)\s*(?:\"|\')(.+?)(?:\"|\')'
regex_pattern9 = r'sources\s*:\s*\[(.+?)\]'
regex_pattern10 = r'\{(.+?)\}'


def re_findall(html, regex):
    match = re.findall(regex, html)
    return match


def re_compile(html, regex):
    match = re.compile(regex).findall(html)
    return match


def unpacked(html):
    from resources.lib.modules import jsunpack
    unpacked = ''
    if jsunpack.detect(html):
        unpacked = jsunpack.unpack(html)
    return unpacked


def parseDOM(html, name='', attrs=None, ret=False):
    if attrs:
        attrs = dict((key, re.compile(value + ('$' if value else ''))) for key, value in six.iteritems(attrs))
    results = dom_parser.parse_dom(html, name, attrs, ret)
    if ret:
        results = [result.attrs[ret.lower()] for result in results]
    else:
        results = [result.content for result in results]
    return results



def remove_codes(string):
    remove = re.compile('<.+?>')
    string = re.sub(remove, '', string)
    return string


def replace_html_entities(string):
    List = [['&lt;', '<'], ['&#60;', '<'], ['&gt;', '>'], ['&#62;', '>'], ['&amp;', '&'], ['&#38;', '&'],
        ['&quot;',' "'], ['&#34;',' "'], ["&apos;", "'"], ["&#39;", "'"], ['\\/', '/']
    ]
    for item in List:
        string = string.replace(item[0], item[1])
    return string


def replaceHTMLCodes(txt):
    txt = re.sub("(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", txt)
    txt = unescape(txt)
    txt = txt.replace("&quot;", "\"")
    txt = txt.replace("&amp;", "&")
    txt = txt.replace("&lt;", "<")
    txt = txt.replace("&gt;", ">")
    txt = txt.replace("&#38;", "&")
    txt = txt.replace("&nbsp;", "")
    txt = txt.replace('&#8230;', '...')
    txt = txt.replace('&#8217;', '\'')
    txt = txt.replace('&#8211;', '-')
    txt = txt.replace("%2B", "+")
    txt = txt.replace("\/", "/")
    txt = txt.replace("\\", "")
    txt = txt.strip()
    return six.ensure_str(txt)


def removeNonAscii(s):
    return "".join(i for i in s if ord(i) < 128)


def _get_keyboard(default="", heading="", hidden=False):
    keyboard = control.keyboard(default, heading, hidden)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return six.ensure_text(keyboard.getText())
    return default


def _add_request_header(_request, headers):
    try:
        if not headers:
            headers = {}
        try:
            scheme = _request.get_type()
        except:
            scheme = 'http'
        referer = headers.get('Referer') if 'Referer' in headers else '%s://%s/' % (scheme, _request.get_host())
        _request.add_unredirected_header('Host', _request.get_host())
        _request.add_unredirected_header('Referer', referer)
        for key in headers:
            _request.add_header(key, headers[key])
    except:
        return


def _get_result(response, limit=None):
    if limit == '0':
        result = response.read(224 * 1024)
    elif limit:
        result = response.read(int(limit) * 1024)
    else:
        result = response.read(5242880)
    try:
        encoding = response.info().getheader('Content-Encoding')
    except:
        encoding = None
    if encoding == 'gzip':
        result = gzip.GzipFile(fileobj=StringIO(result)).read()
    return result


def _basic_request(url, headers=None, post=None, timeout='30', limit=None):
    try:
        try:
            headers.update(headers)
        except:
            headers = {}
        request = Request(url, data=post)
        _add_request_header(request, headers)
        response = urlopen(request, timeout=int(timeout))
        return _get_result(response, limit)
    except:
        return


def request(url, close=True, redirect=True, error=False, verify=True, proxy=None, post=None, headers=None, mobile=False, XHR=False,
            limit=None, referer=None, cookie=None, compression=False, output='', timeout='30', username=None, password=None, as_bytes=False):
    try:
        url = six.ensure_text(url, errors='ignore')
    except Exception:
        pass
    if isinstance(post, dict):
        post = bytes(urlencode(post), encoding='utf-8')
    elif isinstance(post, str) and six.PY3:
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
                if six.PY2:
                    passmgr = urllib2.ProxyBasicAuthHandler()
                else:
                    passmgr = urllib2.HTTPPasswordMgr()
                passmgr.add_password(None, uri=url, user=username, passwd=password)
                handlers += [urllib2.ProxyHandler({'http': '{0}'.format(proxy)}), urllib2.HTTPHandler, urllib2.ProxyBasicAuthHandler(passmgr)]
            else:
                handlers += [urllib2.ProxyHandler({'http':'{0}'.format(proxy)}), urllib2.HTTPHandler]
            opener = urllib2.build_opener(*handlers)
            urllib2.install_opener(opener)
        if output == 'cookie' or output == 'extended' or close is not True:
            cookies = cookielib.LWPCookieJar()
            handlers += [urllib2.HTTPHandler(), urllib2.HTTPSHandler(), urllib2.HTTPCookieProcessor(cookies)]
            opener = urllib2.build_opener(*handlers)
            urllib2.install_opener(opener)
        try:
            import platform
            is_XBOX = platform.uname()[1] == 'XboxOne'
        except Exception:
            is_XBOX = False
        if not verify and sys.version_info >= (2, 7, 12):
            try:
                import ssl
                ssl_context = ssl._create_unverified_context()
                handlers += [urllib2.HTTPSHandler(context=ssl_context)]
                opener = urllib2.build_opener(*handlers)
                urllib2.install_opener(opener)
            except Exception:
                pass
        elif verify and ((2, 7, 8) < sys.version_info < (2, 7, 12) or is_XBOX):
            try:
                import ssl
                try:
                    import _ssl
                    CERT_NONE = _ssl.CERT_NONE
                except Exception:
                    CERT_NONE = ssl.CERT_NONE
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = CERT_NONE
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
            headers['User-Agent'] = UserAgent
        else:
            headers['User-Agent'] = MobileUserAgent
        if 'Referer' in headers:
            pass
        elif referer is None:
            headers['Referer'] = '%s://%s/' % (urlparse(url).scheme, urlparse(url).netloc)
        else:
            headers['Referer'] = referer
        if not 'Accept-Language' in headers:
            headers['Accept-Language'] = 'en-US'
        if 'X-Requested-With' in headers:
            pass
        elif XHR is True:
            headers['X-Requested-With'] = 'XMLHttpRequest'
        if 'Cookie' in headers:
            pass
        elif cookie is not None:
            headers['Cookie'] = cookie
        if 'Accept-Encoding' in headers:
            pass
        elif compression and limit is None:
            headers['Accept-Encoding'] = 'gzip'
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
                    log_utils.log('client - cfScrape Exception', 1)
                elif error is False:
                    return
            elif error is False:
                return
        if output == 'cookie':
            try:
                result = '; '.join(['%s=%s' % (i.name, i.value) for i in cookies])
            except Exception:
                pass
            try:
                result = cf
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
            try:
                cookie = cf
            except Exception:
                pass
            content = response.headers
            result = response.read(5242880)
            if not as_bytes:
                result = six.ensure_text(result, errors='ignore')
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
            result = six.ensure_text(result, errors='ignore')
        return result
    except:
        return


def scrapePage(url, referer=None, headers=None, post=None, cookie=None):
    try:
        if not url:
            return
        url =  "https:" + url if url.startswith('//') else url
        with requests.Session() as session:
            if headers:
                session.headers.update(headers)
            if (referer and not 'Referer' in session.headers):
                session.headers.update({'Referer': referer})
            else:
                elements = urlparse(url)
                base = '%s://%s' % (elements.scheme, (elements.netloc or elements.path))
                session.headers.update({'Referer': base})
            if (cookie and not 'Cookie' in session.headers): # not tested yet, just placed as a idea reminder.
                session.headers.update({'Cookie': cookie})
            if not 'User-Agent' in session.headers:
                session.headers.update({'User-Agent': UserAgent})
            if post:
                page = session.post(url, data=post, timeout=10)
            else:
                page = session.get(url, timeout=10)
            page.encoding = 'utf-8'
            #page.raise_for_status()  # Commented out to make trakt progress option work properly again lol
        return page
    except Exception:
        #log_utils.log('scrapePage', 1)
        return


def url_ok(url): #  Old Code Saved.
    r = scrapePage(url)
    if r.status_code == 200 or r.status_code == 301:
        return True
    else:
        return False

