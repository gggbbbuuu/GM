# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import gzip
import re
import json
from tulip.user_agents import CHROME
from tulip.compat import (
    Request, urlencode, urlopen, cookielib, urllib2, is_py3, basestring, BytesIO, HTTPError, py3_dec
)


class Net:
    """
    This class wraps :mod:`urllib2` and provides an easy way to make http
    requests while taking care of cookies, proxies, gzip compression and
    character encoding.

    Example::

        from addon.common.net import Net
        net = Net()
        response = net.http_GET('http://xbmc.org')
        print response.content
    """

    _cj = cookielib.LWPCookieJar()
    _proxy = None
    _user_agent = CHROME
    _http_debug = False

    def __init__(
            self, url=None, cookie_file='', proxy='', user_agent='', ssl_verify=True,
            http_debug=False, username=None, password=None
    ):
        """
        Kwargs:
            cookie_file (str): Full path to a file to be used to load and save
            cookies to.

            proxy (str): Proxy setting (eg.
            ``'http://user:pass@example.com:1234'``)

            user_agent (str): String to use as the User Agent header. If not
            supplied the class will use a default user agent (chrome)

            http_debug (bool): Set ``True`` to have HTTP header info written to
            the XBMC log for all requests.
        """
        if cookie_file:
            self.set_cookies(cookie_file)
        if proxy:
            self.set_proxy(proxy)
        if user_agent:
            self.set_user_agent(user_agent)
        self._ssl_verify = ssl_verify
        self._http_debug = http_debug
        self.url = url
        self.username = username
        self.password = password
        self._update_opener()

    def set_cookies(self, cookie_file):
        """
        Set the cookie file and try to load cookies from it if it exists.

        Args:
            cookie_file (str): Full path to a file to be used to load and save
            cookies to.
        """
        try:
            self._cj.load(cookie_file, ignore_discard=True)
            self._update_opener()
            return True
        except Exception:
            return False

    def get_cookies(self, as_dict=False):
        """Returns A dictionary containing all cookie information by domain."""
        if as_dict:
            return dict((cookie.name, cookie.value) for cookie in self._cj)
        else:
            # noinspection PyProtectedMember
            return self._cj._cookies

    def save_cookies(self, cookie_file):
        """
        Saves cookies to a file.

        Args:
            cookie_file (str): Full path to a file to save cookies to.
        """
        self._cj.save(cookie_file, ignore_discard=True)

    def set_proxy(self, proxy):
        """
        Args:
            proxy (str): Proxy setting (eg.
            ``'http://user:pass@example.com:1234'``)
        """
        self._proxy = proxy
        self._update_opener()

    def get_proxy(self):
        """Returns string containing proxy details."""
        return self._proxy

    def set_user_agent(self, user_agent):
        """
        Args:
            user_agent (str): String to use as the User Agent header.
        """
        self._user_agent = user_agent

    def get_user_agent(self):
        """Returns user agent string."""
        return self._user_agent

    def _update_opener(self):
        """
        Builds and installs a new opener to be used by all future calls to
        :func:`urllib2.urlopen`.
        """
        if self.username is not None and self.password is not None:
            passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            passmgr.add_password(None, uri=self.url, user=self.username, passwd=self.password)
            handlers = [urllib2.HTTPCookieProcessor(self._cj), urllib2.HTTPBasicAuthHandler(passmgr)]
        else:
            handlers = [urllib2.HTTPCookieProcessor(self._cj), urllib2.HTTPBasicAuthHandler()]

        if self._http_debug:
            handlers += [urllib2.HTTPHandler(debuglevel=1)]
        else:
            handlers += [urllib2.HTTPHandler()]

        if self._proxy:
            handlers += [urllib2.ProxyHandler({'http': self._proxy})]

        try:
            import platform
            node = platform.node().lower()
        except Exception:
            node = ''

        if not self._ssl_verify or node == 'xboxone':

            try:
                import ssl
                ctx = ssl.create_default_context()
                ctx.set_alpn_protocols(['http/1.0', 'http/1.1'])
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                if self._http_debug:
                    handlers += [urllib2.HTTPSHandler(context=ctx, debuglevel=1)]
                else:
                    handlers += [urllib2.HTTPSHandler(context=ctx)]
            except Exception:
                pass

        else:

            try:
                import ssl
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
                ctx.set_alpn_protocols(['http/1.0', 'http/1.1'])
                if self._http_debug:
                    handlers += [urllib2.HTTPSHandler(context=ctx, debuglevel=1)]
                else:
                    handlers += [urllib2.HTTPSHandler(context=ctx)]
            except Exception:
                pass

        opener = urllib2.build_opener(*handlers)
        urllib2.install_opener(opener)

    def http_GET(self, url=None, headers={}, compression=True, timeout=15, jdata=False, limit=None):
        """
        Perform an HTTP GET request.

        Args:
            url (str): The URL to GET.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        """
        if self.url is not None:
            return self._fetch(self.url, headers=headers, compression=compression, timeout=timeout, jdata=jdata, limit=limit)
        else:
            return self._fetch(url, headers=headers, compression=compression, timeout=timeout, jdata=jdata, limit=limit)

    def http_POST(self, url=None, form_data=None, headers={}, compression=True, jdata=False, limit=None):
        """
        Perform an HTTP POST request.

        Args:
            url (str): The URL to POST.

            form_data (dict): A dictionary of form data to POST.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        """
        if self.url is not None:
            return self._fetch(self.url, form_data, headers=headers, compression=compression, jdata=jdata, limit=limit)
        else:
            return self._fetch(url, form_data, headers=headers, compression=compression, jdata=jdata, limit=limit)

    def http_HEAD(self, url=None, headers={}):
        """
        Perform an HTTP HEAD request.

        Args:
            url (str): The URL to GET.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page.
        """
        if self.url is not None:
            request = Request(self.url)
        else:
            request = Request(url)
        request.get_method = lambda: 'HEAD'
        request.add_header('User-Agent', self._user_agent)
        for key in headers:
            request.add_header(key, headers[key])
        response = urlopen(request)
        return HttpResponse(response)

    def http_DELETE(self, url, headers={}):
        """
        Perform an HTTP DELETE request.

        Args:
            url (str): The URL to GET.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page.
        """
        if self.url is not None:
            request = Request(self.url)
        else:
            request = Request(url)
        request.get_method = lambda: 'DELETE'
        request.add_header('User-Agent', self._user_agent)
        for key in headers:
            request.add_header(key, headers[key])
        response = urlopen(request)
        return HttpResponse(response)

    def _fetch(self, url, form_data={}, headers={}, compression=True, jdata=False, timeout=15, limit=None):
        """
        Perform an HTTP GET or POST request.

        Args:
            url (str): The URL to GET or POST.

            form_data (dict): A dictionary of form data to POST. If empty, the

            request will be a GET, if it contains form data it will be a POST.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        """

        url = py3_dec(url)
        req = Request(url)

        if form_data:
            if jdata:
                form_data = json.dumps(form_data)
            elif isinstance(form_data, basestring):
                form_data = form_data
            else:
                form_data = urlencode(form_data, True)
            form_data = form_data.encode('utf-8') if is_py3 else form_data
            req = Request(url, form_data)
        req.add_header('User-Agent', self._user_agent)
        for key in headers:
            req.add_header(key, headers[key])
        if compression:
            req.add_header('Accept-Encoding', 'gzip')
        if jdata:
            req.add_header('Content-Type', 'application/json')
        host = req.host if is_py3 else req.get_host()
        req.add_unredirected_header('Host', host)
        try:
            response = urllib2.urlopen(req, timeout=timeout)
        except HTTPError as e:
            if e.code == 403 and 'cloudflare' in e.hdrs.get('Expect-CT', ''):
                import ssl
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                ctx.set_alpn_protocols(['http/1.0', 'http/1.1'])
                handlers = [urllib2.HTTPSHandler(context=ctx)]
                opener = urllib2.build_opener(*handlers)
                try:
                    response = opener.open(req, timeout=timeout)
                except HTTPError as e:
                    if e.code == 403:
                        ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_1)
                        ctx.set_alpn_protocols(['http/1.0', 'http/1.1'])
                        handlers = [urllib2.HTTPSHandler(context=ctx)]
                        opener = urllib2.build_opener(*handlers)
                        try:
                            response = opener.open(req, timeout=timeout)
                        except HTTPError as e:
                            response = e
            else:
                raise

        return HttpResponse(response, limit=limit)


class HttpResponse:
    """
    This class represents a resoponse from an HTTP request.

    The content is examined and every attempt is made to properly decode it to
    Unicode unless the nodecode property flag is set to True.

    .. seealso::
        :meth:`Net.http_GET`, :meth:`Net.http_HEAD` and :meth:`Net.http_POST`
    """

    # content = ''
    """Unicode encoded string containing the body of the response."""

    def __init__(self, response, limit=None):
        """
        Args:
            response (:class:`mimetools.Message`): The object returned by a call
            to :func:`urllib2.urlopen`.
        """
        self._response = response
        self._nodecode = False
        self._limit = limit

    @property
    def content(self):
        if self._limit:
            html = self._response.read(self._limit)
        else:
            html = self._response.read()
        encoding = None
        try:
            if self._response.headers['content-encoding'].lower() == 'gzip':
                html = gzip.GzipFile(fileobj=BytesIO(html)).read()
        except Exception:
            pass

        if self._nodecode:
            return html

        try:
            content_type = self._response.headers['content-type']
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[-1]
        except Exception:
            pass

        if encoding is None:
            epattern = r'<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"'
            epattern = epattern.encode('utf8') if is_py3 else epattern
            r = re.search(epattern, html, re.IGNORECASE)
            if r:
                encoding = r.group(1).decode('utf8') if is_py3 else r.group(1)

        if encoding is not None:
            html = html.decode(encoding, errors='ignore')
        else:
            html = html.decode('ascii', errors='ignore') if is_py3 else html
        return html

    def get_headers(self, as_dict=False):
        """Returns headers returned by the server.
        If as_dict is True, headers are returned as a dictionary otherwise a list"""
        if as_dict:
            hdrs = {}
            for item in list(self._response.info().items()):
                if item[0].title() not in list(hdrs.keys()):
                    hdrs.update({item[0].title(): item[1]})
                else:
                    hdrs.update({item[0].title(): ','.join([hdrs[item[0].title()], item[1]])})
            return hdrs
        else:
            return self._response.info()._headers if is_py3 else [(x.split(':')[0].strip(), x.split(':')[1].strip()) for x in self._response.info().headers]

    def get_url(self):
        """
        Return the URL of the resource retrieved, commonly used to determine if
        a redirect was followed.
        """
        return self._response.geturl()

    def get_json(self):

        return json.loads(self.content)

    def nodecode(self, nodecode):
        """
        Sets whether or not content returns decoded text
        nodecode (bool): Set to ``True`` to allow content to return undecoded data
        suitable to write to a binary file
        """
        self._nodecode = bool(nodecode)
        return self
