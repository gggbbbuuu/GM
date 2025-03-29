# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import print_function

import re
from collections import namedtuple
from tulip.compat import iteritems, unicode, basestring, is_py2
try:
    from tulip.log import log_debug
except Exception:
    log_debug = None

tag_re = re.compile(r'''(?=<(?P<tag>[a-zA-Z]+)(?P<attr>.*?)(?P<end>/)?>(?:(?P<inner>.*?)</\s*(?P=tag)\s*>)?)''', re.MULTILINE | re.DOTALL)
attr_re = re.compile(r'''\s*(?P<key>[\w-]+)\s*(?:=\s*(?P<quote>["']?)(?P<value>.*?)(?P=quote)\s*)?''')
Tag = namedtuple("Tag", "tag attributes text")
DomMatch = namedtuple('DOMMatch', ['attrs', 'content'])
re_type = type(re.compile(''))


def itertags(html, tag):

    """
    Brute force regex based HTML tag parser. This is a rough-and-ready searcher to find HTML tags when
    standards compliance is not required. Will find tags that are commented out, or inside script tag etc.
    Shamelessly taken from streamlink library: https://github.com/streamlink/streamlink

    :param html: HTML page
    :param tag: tag name to find
    :return: generator with Tags
    """

    for match in tag_re.finditer(html):

        if match.group("tag") == tag:

            attrs = dict((a.group("key").lower(), a.group("value")) for a in attr_re.finditer(match.group("attr")))

            yield Tag(match.group("tag"), attrs, match.group("inner"))


def itertags_wrapper(html, tag, attrs=None, ret=False):

    try:

        result = list(itertags(html, tag))

        if isinstance(attrs, dict):

            attrs = list(iteritems(attrs))

            result = [
                i for i in result if any(
                    [a for a in attrs if any([a[0] == k and re.match(a[1], v) for k, v in iteritems(i.attributes)])]
                )
            ]

        if ret:

            # noinspection PyTypeChecker
            result = [i.attributes[ret] for i in result if ret in i.attributes]

    except Exception:

        result = []

    return result


def parseDOM(html, name=u"", attrs=None, ret=False):

    """
    :param html:
        String to parse, or list of strings to parse.
    :type html:
        string or list
    :param name:
        Element to match ( for instance "span" )
    :type name:
        string
    :param attrs:
        Dictionary with attributes you want matched in the elment (for
        instance { "id": "span3", "class": "oneclass.*anotherclass",
        "attribute": "a random tag" } )
    :type attrs:
        dict
    :param ret:
        Attribute in element to return value of. If not set(or False), returns
        content of DOM element.
    :type ret:
        string
    """

    if attrs is None:
        attrs = {}

    # log_debug("Name: " + repr(name) + " - Attrs:" + repr(attrs) + " - Ret: " + repr(ret) + " - HTML: " + str(type(html)))

    if isinstance(name, basestring):  # Should be handled

        try:
            name = name.decode("utf-8")
        except Exception:
            pass
            # log_debug("Couldn't decode name binary string: " + repr(name))

    if isinstance(html, basestring):
        try:
            html = [html.decode("utf-8")]  # Replace with chardet thingy
        except Exception:
            html = [html]
    elif isinstance(html, unicode):
        html = [html]
    elif not isinstance(html, list):
        if log_debug:
            log_debug("Input isn't list or string/unicode.")
        else:
            print("Input isn't list or string/unicode.")
        return u""

    if not name.strip():
        if log_debug:
            log_debug("Missing tag name")
        else:
            print("Missing tag name")
        return u""

    ret_lst = []
    for item in html:
        temp_item = re.compile('(<[^>]*?\n[^>]*?>)').findall(item)
        for match in temp_item:
            item = item.replace(match, match.replace("\n", " "))

        lst = _getDOMElements(item, name, attrs)

        if isinstance(ret, basestring):
            # log_debug("Getting attribute %s content for %s matches " % (ret, len(lst) ))
            lst2 = []
            for match in lst:
                lst2 += _getDOMAttributes(match, name, ret)
            lst = lst2
        else:
            # log_debug("Getting element content for %s matches " % len(lst))
            lst2 = []
            for match in lst:
                # log_debug("Getting element content for %s" % match)
                temp = _getDOMContent(item, name, match, ret).strip()
                item = item[item.find(temp, item.find(match)) + len(temp):]
                lst2.append(temp)
            lst = lst2
        ret_lst += lst

    # log_debug("Done: " + repr(ret_lst))
    return ret_lst


def _getDOMContent(html, name, match, ret):  # Cleanup
    # log_debug("match: " + match)

    endstr = u"</" + name  # + ">"

    start = html.find(match)
    end = html.find(endstr, start)
    pos = html.find("<" + name, start + 1 )

    # log_debug(str(start) + " < " + str(end) + ", pos = " + str(pos) + ", endpos: " + str(end))

    while pos < end and pos != -1:  # Ignore too early </endstr> return
        tend = html.find(endstr, end + len(endstr))
        if tend != -1:
            end = tend
        pos = html.find("<" + name, pos + 1)
        # log_debug("loop: " + str(start) + " < " + str(end) + " pos = " + str(pos))

    # log_debug("start: %s, len: %s, end: %s" % (start, len(match), end))
    if start == -1 and end == -1:
        result = u""
    elif start > -1 and end > -1:
        result = html[start + len(match):end]
    elif end > -1:
        result = html[:end]
    elif start > -1:
        result = html[start + len(match):]

    if ret:
        endstr = html[end:html.find(">", html.find(endstr)) + 1]
        result = match + result + endstr

    # log_debug("done result length: " + str(len(result)))
    return result


def _getDOMAttributes(match, name, ret):

    lst = re.compile('<' + name + '.*?' + ret + '=([\'"].[^>]*?[\'"])>', re.M | re.S).findall(match)
    if len(lst) == 0:
        lst = re.compile('<' + name + '.*?' + ret + '=(.[^>]*?)>', re.M | re.S).findall(match)
    ret = []
    for tmp in lst:
        cont_char = tmp[0]
        if cont_char in "'\"":
            # log_debug("Using %s as quotation mark" % cont_char)

            # Limit down to next variable.
            if tmp.find('=' + cont_char, tmp.find(cont_char, 1)) > -1:
                tmp = tmp[:tmp.find('=' + cont_char, tmp.find(cont_char, 1))]

            # Limit to the last quotation mark
            if tmp.rfind(cont_char, 1) > -1:
                tmp = tmp[1:tmp.rfind(cont_char)]
        else:
            # log_debug("No quotation mark found")
            if tmp.find(" ") > 0:
                tmp = tmp[:tmp.find(" ")]
            elif tmp.find("/") > 0:
                tmp = tmp[:tmp.find("/")]
            elif tmp.find(">") > 0:
                tmp = tmp[:tmp.find(">")]

        ret.append(tmp.strip())

    # log_debug("Done: " + repr(ret))
    return ret


def _getDOMElements(item, name, attrs):

    lst = []
    for key in attrs:
        lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"].*?>))', re.M | re.S).findall(item)
        if len(lst2) == 0 and attrs[key].find(" ") == -1:  # Try matching without quotation marks
            lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=' + attrs[key] + '.*?>))', re.M | re.S).findall(item)

        if len(lst) == 0:
            # log_debug("Setting main list " + repr(lst2))
            lst = lst2
            lst2 = []
        else:
            # log_debug("Setting new list " + repr(lst2))
            test = list(range(len(lst)))
            test.reverse()
            for i in test:  # Delete anything missing from the next list.
                if not lst[i] in lst2:
                    # log_debug("Purging mismatch " + str(len(lst)) + " - " + repr(lst[i]))
                    del(lst[i])

    if len(lst) == 0 and attrs == {}:
        # log_debug("No list found, trying to match on name only")
        lst = re.compile('(<' + name + '>)', re.M | re.S).findall(item)
        if len(lst) == 0:
            lst = re.compile('(<' + name + ' .*?>)', re.M | re.S).findall(item)

    # log_debug("Done: " + str(type(lst)))
    return lst


def __get_dom_content(html, name, match):
    if match.endswith('/>'): return ''

    # override tag name with tag from match if possible
    tag = re.match('<([^\s/>]+)', match)
    if tag: name = tag.group(1)

    start_str = '<%s' % (name)
    end_str = "</%s" % (name)

    # start/end tags without matching case cause issues
    start = html.find(match)
    end = html.find(end_str, start)
    pos = html.find(start_str, start + 1)

    while pos < end and pos != -1:  # Ignore too early </endstr> return
        tend = html.find(end_str, end + len(end_str))
        if tend != -1:
            end = tend
        pos = html.find(start_str, pos + 1)

    if start == -1 and end == -1:
        result = ''
    elif start > -1 and end > -1:
        result = html[start + len(match):end]
    elif end > -1:
        result = html[:end]
    elif start > -1:
        result = html[start + len(match):]
    else:
        result = ''

    return result


def __get_dom_elements(item, name, attrs):
    if not attrs:
        pattern = r'(<%s(?:\s[^>]*>|/?>))' % (name)
        this_list = re.findall(pattern, item, re.M | re.S | re.I)
    else:
        last_list = None
        for key, value in iteritems(attrs):
            value_is_regex = isinstance(value, re_type)
            value_is_str = isinstance(value, basestring)
            if value_is_str:
                value = re.compile(value)
            pattern = r'''(<{tag}[^>]*\s{key}=(?P<delim>['"])(.*?)(?P=delim)[^>]*>)'''.format(tag=name, key=key)
            re_list = re.findall(pattern, item, re.M | re.S | re.I)

            this_list = [r[0] for r in re_list if re.match(value, r[2])]

            if not this_list:
                has_space = ' ' in value.pattern
                if not has_space:
                    pattern = r'''(<{tag}[^>]*\s{key}=([^\s/>]*)[^>]*>)'''.format(tag=name, key=key)
                    re_list = re.findall(pattern, item, re.M | re. S | re.I)
                    if value_is_regex:
                        this_list = [r[0] for r in re_list if re.match(value, r[1])]
                    else:
                        this_list = [r[0] for r in re_list if value == r[1]]

            if last_list is None:
                last_list = this_list
            else:
                last_list = [item for item in this_list if item in last_list]
        this_list = last_list

    return this_list


def __get_attribs(element):

    attribs = {}

    for match in re.finditer(
            r'''\s+(?P<key>[^=]+)=\s*(?:(?P<delim>["'])(?P<value1>.*?)(?P=delim)|(?P<value2>[^"'][^>\s]*))''', element
    ):

        match = match.groupdict()
        value1 = match.get('value1')
        value2 = match.get('value2')
        value = value1 if value1 is not None else value2

        if value is None:
            continue

        attribs[match['key'].lower().strip()] = value

    return attribs


def parseDOM2(html, name='', attrs=None, ret=False):
    if attrs is None:
        attrs = {}
    name = name.strip()
    if isinstance(html, unicode) or isinstance(html, DomMatch):
        html = [html]
    elif isinstance(html, basestring) and is_py2:
        try:
            html = [html.decode("utf-8")]  # Replace with chardet thingy
        except:
            try:
                html = [html.decode("utf-8", "replace")]
            except Exception:
                html = [html]
    elif not isinstance(html, list):
        return ''

    if not name:
        return ''

    if not isinstance(attrs, dict):
        return ''

    if ret:
        if not isinstance(ret, list):
            ret = [ret]
        ret = set([key.lower() for key in ret])

    all_results = []
    for item in html:
        if isinstance(item, DomMatch):
            item = item.content

        results = []
        for element in __get_dom_elements(item, name, attrs):
            attribs = __get_attribs(element)
            if ret and not ret <= set(attribs.keys()):
                continue
            temp = __get_dom_content(item, name, element).strip()
            results.append(DomMatch(attribs, temp))
            item = item[item.find(temp, item.find(element)):]
        all_results += results

    return all_results


def get_dom(html, tag):

    """
    Simple and fast dom parser
    """

    start_str = '<%s' % (tag.lower())
    end_str = '</%s' % (tag.lower())

    results = []
    html = html.lower()
    while html:
        start = html.find(start_str)
        end = html.find(end_str, start)
        pos = html.find(start_str, start + 1)
        while pos < end and pos != -1:
            tend = html.find(end_str, end + len(end_str))
            if tend != -1:
                end = tend
            pos = html.find(start_str, pos + 1)

        if start == -1 and end == -1:
            break
        elif start > -1 and end > -1:
            result = html[start:end]
        elif end > -1:
            result = html[:end]
        elif start > -1:
            result = html[start:]
        else:
            break

        results.append(result)
        html = html[start + len(start_str):]

    return results


def parse_headers(string):

    """
    Converts a multi-line response/request headers string into a dictionary
    :param string: string of headers
    :return: dictionary of response headers
    """

    headers = dict([line.partition(': ')[::2] for line in string.splitlines()])

    return headers


__all__ = ['itertags', 'parseDOM', 'parseDOM2', 'itertags_wrapper', 'parse_headers']
