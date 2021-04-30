# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import absolute_import

import re, unicodedata
from tulip.compat import unicode, unescape


def get(title, lower=True):

    if title is None:
        return

    title = re.sub(r'&#(\d+);', '', title)
    title = re.sub(r'(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title)
    title = re.sub(r'\n|([[].+?[]])|([(].+?[)])|\s(vs|v[.])\s|([:;\-,\'\s.?])|\s', '', title)

    if lower:

        title = title.lower()

    return title


def query(title):

    if title is None:
        return

    title = title.replace("'", '').rsplit(':', 1)[0]

    return title


def normalize(title):

    try:

        try:
            return title.decode('ascii').encode('utf-8')
        except Exception:
            pass

        t = ''
        for i in title:
            c = unicodedata.normalize('NFKD', unicode(i, 'ISO-8859-1'))
            c = c.encode('ascii', 'ignore').strip()
            if i == ' ':
                c = i
            t += c

        return t.encode('utf-8')

    except Exception:

        return title


def strip_accents(string):

    result = ''.join(c for c in unicodedata.normalize('NFD', string) if unicodedata.category(c) != 'Mn')

    return result


def stripTags(html):

    sub_start = html.find("<")
    sub_end = html.find(">")
    while sub_end > sub_start > -1:
        html = html.replace(html[sub_start:sub_end + 1], "").strip()
        sub_start = html.find("<")
        sub_end = html.find(">")

    return html


def replaceHTMLCodes(txt):

    txt = re.sub("(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", txt)
    txt = unescape(txt)
    txt = txt.replace("&quot;", "\"")
    txt = txt.replace("&amp;", "&")
    txt = txt.replace("&#38;", "&")
    txt = txt.replace("&nbsp;", " ")
    txt = txt.replace('&#8230;', '...')
    txt = txt.replace('&#8217;', '\'')
    txt = txt.replace('&#8211;', '-')

    return txt


__all__ = ['get', 'replaceHTMLCodes', 'get', 'query', 'normalize', 'strip_accents']
