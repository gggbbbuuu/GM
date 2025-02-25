# -*- coding: utf-8 -*-

'''
    Tulip routine libraries, based on lambda's lamlib
    Author Twilight0
    Modified snippet from compat module taken from streamlink

        License summary below, for more details please read license.txt file

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 2 of the License, or
        (at your option) any later version.
        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.
        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from __future__ import absolute_import

import sys

is_py2 = sys.version_info[0] == 2
is_py3 = sys.version_info[0] == 3

if sys.version_info < (2, 7, 0):

    from tulip.ordereddict import OrderedDict

else:

    from collections import OrderedDict


if is_py2:

    string = str
    str = unicode
    range = xrange
    from itertools import izip
    zip = izip
    unicode = unicode
    basestring = basestring

    def bytes(b, encoding="ascii"):

        return string(b)

    def iteritems(d, **kw):

        return d.iteritems(**kw)

    import tulip.concurrent.futures
    concurrent_futures = tulip.concurrent.futures

elif is_py3:

    bytes = string = bytes
    str = unicode = basestring = str
    range = range
    zip = zip

    def iteritems(d, **kw):

        return iter(d.items(**kw))

    import concurrent.futures
    concurrent_futures = concurrent.futures


def py2_enc(s, encoding='utf-8'):

    if is_py2 and isinstance(s, unicode):
        s = s.encode(encoding)

    return s


def py2_uni(s, encoding='utf-8'):

    if is_py2 and isinstance(s, string):
        s = unicode(s, encoding)

    return s


def py3_dec(d, encoding='utf-8'):

    if is_py3 and isinstance(d, bytes):
        d = d.decode(encoding)

    return d


try:
    from sqlite3 import dbapi2 as database
except ImportError:
    from pysqlite2 import dbapi2 as database

# Python 2
try:

    from urlparse import urlparse, urlunparse, urljoin, parse_qsl, urlsplit, urlunsplit, parse_qs
    from urllib import quote, unquote, urlencode, URLopener, quote_plus, unquote_plus, addinfourl
    import Queue
    import cookielib
    import urllib2
    import httplib
    import BaseHTTPServer
    import cPickle as pickle
    from cStringIO import StringIO
    from SocketServer import ThreadingMixIn
    from HTMLParser import HTMLParser
    unescape = HTMLParser().unescape
    HTTPError = urllib2.HTTPError
    BytesIO = StringIO

# Python 3:
except ImportError:

    from http import client as httplib, cookiejar as cookielib
    from html import unescape
    import urllib.request as urllib2
    import http.server as BaseHTTPServer
    from socketserver import ThreadingMixIn
    from io import StringIO, BytesIO
    from urllib.parse import (
        urlparse, urlunparse, urljoin, quote, unquote, parse_qsl, parse_qs, urlencode, urlsplit, urlunsplit,
        unquote_plus, quote_plus
    )
    from urllib.response import addinfourl
    from urllib.error import HTTPError
    import queue as Queue
    import pickle
    URLopener = urllib2.URLopener

finally:

    urlopen = urllib2.urlopen
    Request = urllib2.Request


__all__ = [
    "is_py2", "is_py3", "str", "bytes", "urlparse", "urlunparse", "urljoin", "parse_qsl", "quote", "unquote", "Queue",
    "range", "urlencode", "zip", "urlsplit", "urlunsplit", "cookielib", "URLopener", "quote_plus", "unescape",
    "parse_qs", "unquote_plus", "urllib2", "unicode", "database", "basestring", "urlopen", "Request", "OrderedDict",
    "iteritems", "BaseHTTPServer", "ThreadingMixIn", "addinfourl", "StringIO", "py2_enc", "py2_uni", "py3_dec",
    "HTTPError", "pickle", "httplib", "BytesIO", "concurrent_futures"
]
