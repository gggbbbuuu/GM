"""
    common XBMC Module
    Copyright (C) 2011 t0mm0

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import gzip
import json
import re
import six
from six.moves import urllib_request, urllib_parse, urllib_error, urllib_response, http_cookiejar
import socket
import sys
import certifi
try:
    import xbmcvfs
except ImportError:
    xbmcvfs = None

# Set Global timeout - Useful for slow connections and Putlocker.
socket.setdefaulttimeout(10)

if xbmcvfs:
    # noinspection PyUnresolvedReferences
    CERT_FILE = xbmcvfs.translatePath('special://xbmc/system/certs/cacert.pem')
else:
    CERT_FILE = certifi.where()


class NoRedirection(urllib_request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib_response.addinfourl(fp, headers, req.get_full_url() if six.PY2 else req.full_url)
        if sys.version_info < (3, 9, 0):
            infourl.status = code
            infourl.code = code
        return infourl
    http_error_300 = http_error_302
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302


# Chrome150's TLS 1.2 cipher order, in OpenSSL names (curl-impersonate v2.2.3).
# TLS 1.3 suites stay at the linked OpenSSL's defaults: Python exposes no
# set_ciphersuites, and the defaults are already the modern three.
CHROME150_CIPHERS = (
    'ECDHE-ECDSA-AES128-GCM-SHA256:'
    'ECDHE-RSA-AES128-GCM-SHA256:'
    'ECDHE-ECDSA-AES256-GCM-SHA384:'
    'ECDHE-RSA-AES256-GCM-SHA384:'
    'ECDHE-ECDSA-CHACHA20-POLY1305:'
    'ECDHE-RSA-CHACHA20-POLY1305:'
    'ECDHE-RSA-AES128-SHA:'
    'ECDHE-RSA-AES256-SHA:'
    'AES128-GCM-SHA256:'
    'AES256-GCM-SHA384:'
    'AES128-SHA:'
    'AES256-SHA'
)


def modern_context(verify=True):
    """
    An SSLContext with a modernized handshake, as far as stock ssl allows.

    Chrome150-ordered TLS 1.2 ciphers, ALPN, no legacy protocols. This is what
    already passes Cloudflare's bar on new stacks (Python 3.14 + OpenSSL 3.x
    resolves bot-walled hosts with plain urllib); applied explicitly, old
    stacks get what new stacks get for free.

    Deliberately not impersonation, and honest about the gaps: no GREASE, no
    curve/group order, no extension ordering, no ECH, HTTP/1.1 only. If a host
    allowlists exact Chrome JA3 instead of just requiring a modern client,
    this fails like any other stdlib handshake.
    """
    import ssl
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if verify:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        try:
            ctx.load_default_certs()
        except Exception:
            pass
        try:
            ctx.load_verify_locations(cafile=CERT_FILE)
        except Exception:
            pass
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers(CHROME150_CIPHERS)
    except Exception:
        pass
    try:
        ctx.set_alpn_protocols(['http/1.1'])
    except Exception:
        pass
    for flag in ('OP_NO_SSLv2', 'OP_NO_SSLv3', 'OP_NO_TLSv1',
                 'OP_NO_TLSv1_1', 'OP_NO_COMPRESSION'):
        try:
            ctx.options |= getattr(ssl, flag)
        except Exception:
            pass
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    except Exception:
        pass
    return ctx


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

    _cj = http_cookiejar.LWPCookieJar()
    _proxy = None
    _user_agent = 'python-urllib'
    _http_debug = False
    _default_timeout = 20

    def __init__(self, cookie_file='', proxy='', user_agent='', ssl_verify=True, http_debug=False, timeout=20, modern_tls=False):
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

            timeout (int): Default timeout in seconds for requests made by this instance.

            modern_tls (bool): Set ``True`` to handshake with a modernized TLS
            profile (Chrome150 cipher order, ALPN, no legacy protocols) instead
            of the interpreter defaults. Opt-in; off by default, existing
            behaviour unchanged. See :func:`modern_context` for what this is
            and is not.
        """
        if cookie_file:
            self.set_cookies(cookie_file)
        if proxy:
            self.set_proxy(proxy)
        if user_agent:
            self.set_user_agent(user_agent)
        self._ssl_verify = ssl_verify
        self._http_debug = http_debug
        self._default_timeout = timeout
        self._modern_tls = modern_tls
        self._modern_opener = None
        if modern_tls:
            self._modern_opener = self._modern_opener_for()
        self._update_opener()

    def _modern_opener_for(self):
        """A private opener whose HTTPS handler uses the modernized context."""
        ctx = modern_context(verify=self._ssl_verify)
        handlers = [urllib_request.HTTPCookieProcessor(self._cj),
                    urllib_request.HTTPBasicAuthHandler(),
                    urllib_request.HTTPSHandler(context=ctx)]
        if self._proxy:
            handlers += [urllib_request.ProxyHandler({'http': self._proxy})]
        return urllib_request.build_opener(*handlers)

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
        except:
            return False

    def get_cookies(self, as_dict=False):
        """Returns A dictionary containing all cookie information by domain."""
        if as_dict:
            return dict((cookie.name, cookie.value) for cookie in self._cj)
        else:
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
        handlers = [urllib_request.HTTPCookieProcessor(self._cj), urllib_request.HTTPBasicAuthHandler()]

        if self._http_debug:
            handlers += [urllib_request.HTTPHandler(debuglevel=1)]
        else:
            handlers += [urllib_request.HTTPHandler()]

        if self._proxy:
            handlers += [urllib_request.ProxyHandler({'http': self._proxy})]

        try:
            import platform
            node = platform.node().lower()
        except:
            node = ''

        if not self._ssl_verify or node == 'xboxone':
            try:
                import ssl
                ctx = ssl.create_default_context()
                ctx.maximum_version = ssl.PROTOCOL_TLSv1_3
                ctx.set_alpn_protocols(['http/1.1'])
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                if self._http_debug:
                    handlers += [urllib_request.HTTPSHandler(context=ctx, debuglevel=1)]
                else:
                    handlers += [urllib_request.HTTPSHandler(context=ctx)]
            except:
                pass
        else:
            try:
                import ssl
                ctx = ssl.create_default_context(cafile=CERT_FILE)
                ctx.maximum_version = ssl.PROTOCOL_TLSv1_3
                ctx.set_alpn_protocols(['http/1.1'])
                if self._http_debug:
                    handlers += [urllib_request.HTTPSHandler(context=ctx, debuglevel=1)]
                else:
                    handlers += [urllib_request.HTTPSHandler(context=ctx)]
            except:
                pass

        opener = urllib_request.build_opener(*handlers)
        urllib_request.install_opener(opener)

    def http_GET(self, url, headers={}, compression=True, redirect=True, timeout=None):
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
        return self._fetch(url, headers=headers, compression=compression, redirect=redirect, timeout=timeout)

    def http_POST(self, url, form_data, headers={}, compression=True, jdata=False, redirect=True, timeout=None):
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
        return self._fetch(url, form_data, headers=headers, compression=compression, jdata=jdata, redirect=redirect, timeout=timeout)

    def http_PATCH(self, url, form_data, headers={}, compression=True, jdata=True, redirect=True, timeout=None):
        """
        Perform an HTTP PATCH request.

        Args:
            url (str): The URL to PATCH.
            form_data (dict): A dictionary of form data to PATCH.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)
            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        """
        return self._fetch(url, form_data, headers=headers, compression=compression, jdata=jdata, redirect=redirect, timeout=timeout, method='PATCH')

    def http_HEAD(self, url, headers={}):
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
        request = urllib_request.Request(url)
        request.get_method = lambda: 'HEAD'
        request.add_header('User-Agent', self._user_agent)
        for key in headers:
            request.add_header(key, headers[key])
        response = urllib_request.urlopen(request)
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
        request = urllib_request.Request(url)
        request.get_method = lambda: 'DELETE'
        request.add_header('User-Agent', self._user_agent)
        for key in headers:
            request.add_header(key, headers[key])
        response = urllib_request.urlopen(request)
        return HttpResponse(response)

    def _fetch(self, url, form_data=None, headers={}, compression=True, jdata=False, redirect=True, timeout=None, method=None):
        """
        Perform an HTTP GET, POST or PATCH request.

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
        if timeout is None:
            timeout = self._default_timeout
        if form_data is not None:
            if jdata:
                form_data = json.dumps(form_data)
            elif isinstance(form_data, six.string_types):
                form_data = form_data
            else:
                form_data = urllib_parse.urlencode(form_data, True)
            form_data = form_data.encode('utf-8') if six.PY3 else form_data
            req = urllib_request.Request(url, form_data)
        else:
            req = urllib_request.Request(url)

        if method:
            req.get_method = lambda: method

        req.add_header('User-Agent', self._user_agent)
        for key in headers:
            req.add_header(key, headers[key])
        if compression:
            req.add_header('Accept-Encoding', 'gzip')
        if jdata:
            req.add_header('Content-Type', 'application/json')
        host = req.host if six.PY3 else req.get_host()
        req.add_unredirected_header('Host', host)
        try:
            if not redirect:
                opener = urllib_request.build_opener(NoRedirection())
                response = opener.open(req, timeout=timeout)
            elif self._modern_opener is not None:
                response = self._modern_opener.open(req, timeout=timeout)
            else:
                response = urllib_request.urlopen(req, timeout=timeout)
        except urllib_error.HTTPError as e:
            if e.code == 403 and 'cloudflare' in e.hdrs.get('server', ''):
                if 'challenge' in e.hdrs.get('cf-mitigated', ''):
                    raise
                import ssl
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                ctx.set_alpn_protocols(['http/1.1'])
                handlers = [urllib_request.HTTPSHandler(context=ctx)]
                opener = urllib_request.build_opener(*handlers)
                try:
                    response = opener.open(req, timeout=timeout)
                except urllib_error.HTTPError as e:
                    if e.code == 403:
                        ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_1)
                        ctx.set_alpn_protocols(['http/1.1'])
                        handlers = [urllib_request.HTTPSHandler(context=ctx)]
                        opener = urllib_request.build_opener(*handlers)
                        try:
                            response = opener.open(req, timeout=timeout)
                        except urllib_error.HTTPError:
                            raise
                        except urllib_error.URLError:
                            raise
                    else:
                        raise
            else:
                raise

        return HttpResponse(response)


class ModernSession:
    """
    A small session wrapper over :class:`Net` with the modern TLS handshake.

    Mirrors the subset of the ``requests``-style session surface that Kodi
    providers use: ``get``/``post`` returning objects with ``.text``,
    ``.content``, ``.status_code`` and ``.url``, raw cookie-string seeding
    with persistence across requests, and ``close()``. Construct via
    :func:`modern_session`; ``Net`` itself is untouched.
    """

    def __init__(self, net, cookie=None):
        self._net = net
        if cookie:
            self.seed(cookie)

    def seed(self, cookie):
        """Applies a raw ``'name=value; name=value'`` cookie string."""
        try:
            from six.moves import http_cookiejar as _jar
        except ImportError:
            return
        try:
            from urllib.parse import urlsplit as _split
        except ImportError:
            from urlparse import urlsplit as _split
        for part in str(cookie).split(';'):
            part = part.strip()
            if '=' not in part:
                continue
            name, value = part.split('=', 1)
            name, value = name.strip(), value.strip()
            if name and value:
                item = _jar.Cookie(
                    version=0, name=name, value=value, port=None, port_specified=False,
                    domain='', domain_specified=False, domain_initial_dot=False,
                    path='/', path_specified=True, secure=False, expires=None,
                    discard=True, comment=None, comment_url=None, rest={})
                self._net._cj.set_cookie(item)

    def get(self, url, headers=None, timeout=None):
        return self._net.http_GET(
            url, headers=headers or {},
            timeout=timeout if timeout is not None else self._net._default_timeout)

    def post(self, url, data=None, headers=None, timeout=None):
        return self._net.http_POST(
            url, data or {},
            headers=headers or {},
            timeout=timeout if timeout is not None else self._net._default_timeout)

    def close(self):
        pass


def modern_session(cookie=None, user_agent='', timeout=20):
    """
    A :class:`ModernSession` over ``Net(modern_tls=True)``.

    Args:
        cookie (str): Optional raw ``'name=value; ...'`` cookie string.
        user_agent (str): User-Agent header; callers pass their own (eg. a
        non-JS agent that walks past proof-of-work gates on its own).
        timeout (int): Default timeout in seconds.
    """
    return ModernSession(Net(user_agent=user_agent, timeout=timeout, modern_tls=True), cookie=cookie)


class HttpResponse:
    """
    This class represents a resoponse from an HTTP request.

    The content is examined and every attempt is made to properly decode it to
    Unicode unless the nodecode property flag is set to True.

    .. seealso::
        :meth:`Net.http_GET`, :meth:`Net.http_HEAD` and :meth:`Net.http_POST`
    """

    # content = ''
    """Unicode encoded string containing the body of the reponse."""

    def __init__(self, response):
        """
        Args:
            response (:class:`mimetools.Message`): The object returned by a call
            to :func:`urllib2.urlopen`.
        """
        self._response = response
        self._nodecode = False

    @property
    def content(self):
        html = self._response.read()
        encoding = None
        try:
            if self._response.headers.get('content-encoding', '').lower() == 'gzip':
                html = gzip.GzipFile(fileobj=six.BytesIO(html)).read()
        except (IOError, EOFError):
            pass

        if self._nodecode:
            return html

        try:
            content_type = self._response.headers.get('content-type', '')
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[-1]
        except:
            pass

        if encoding is None:
            epattern = r'<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"'
            epattern = epattern.encode('utf8') if six.PY3 else epattern
            r = re.search(epattern, html, re.IGNORECASE)
            if r:
                encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)

        if encoding is not None:
            html = html.decode(encoding, errors='ignore')
        else:
            html = html.decode('ascii', errors='ignore') if six.PY3 else html
        return html

    @property
    def status_code(self):
        """HTTP status of the response (eg. 200)."""
        try:
            return self._response.status
        except AttributeError:
            return self._response.code

    @property
    def text(self):
        """Decoded body text; same as :attr:`content` unless nodecode is set."""
        result = self.content
        if isinstance(result, bytes):
            try:
                return result.decode('utf-8', errors='replace')
            except Exception:
                return ''
        return result

    @property
    def json(self):
        """Returns JSON decoded body as a python dict/list."""
        return json.loads(self.content)

    def get_json(self):
        """Convenience method for backwards compatibility returning json."""
        return self.json

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
            return self._response.info()._headers if six.PY3 else [(x.split(':')[0].strip(), x.split(':')[1].strip()) for x in self._response.info().headers]

    def get_cookies(self, as_dict=False):
        """Returns cookies returned by the server.
        If as_dict is True, cookies are returned as a dictionary otherwise a string"""
        cookies = {}
        cookie_list = []
        for item in self.get_headers():
            if item[0] == 'Set-Cookie':
                x = item[1].split(';')[0]
                k, v = x.split('=', 1)
                cookies.update({k: v})
                cookie_list.append(x)
        return cookies if as_dict else '; '.join(cookie_list)

    def get_url(self):
        """
        Return the URL of the resource retrieved, commonly used to determine if
        a redirect was followed.
        """
        return self._response.geturl()

    def get_redirect_url(self):
        """
        Return the redirect URL of the resource retrieved
        """
        return self._response.headers.get('location')

    def nodecode(self, nodecode):
        """
        Sets whether or not content returns decoded text
        nodecode (bool): Set to ``True`` to allow content to return undecoded data
        suitable to write to a binary file
        """
        self._nodecode = bool(nodecode)
        return self

    def close(self):
        """Closes the underlying HTTP response stream."""
        if hasattr(self._response, 'close'):
            self._response.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
