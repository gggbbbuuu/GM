import re
from collections import namedtuple

re_type = type(re.compile(''))
DomMatch = namedtuple('DOMMatch', ['attrs', 'content'])

def parseDOM(html, name="", attrs=None, ret=False):

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

    if isinstance(name, bytes):
        try:
            name = name.decode("utf-8")
        except Exception:
            pass

    if isinstance(html, bytes):
        try:
            html = [html.decode("utf-8")]  # Replace with chardet thingy
        except Exception:
            html = [html]
    elif isinstance(html, str):
        html = [html]
    elif not isinstance(html, list):
        print("Input isn't list or string.")
        return ""

    if not name.strip():
        print("Missing tag name")
        return ""

    ret_lst = []
    for item in html:
        temp_item = re.compile('(<[^>]*?\n[^>]*?>)').findall(item)
        for match in temp_item:
            item = item.replace(match, match.replace("\n", " "))

        lst = _getDOMElements(item, name, attrs)

        if isinstance(ret, str):
            lst2 = []
            for match in lst:
                lst2 += _getDOMAttributes(match, name, ret)
            lst = lst2
        else:
            lst2 = []
            for match in lst:
                temp = _getDOMContent(item, name, match, ret).strip()
                item = item[item.find(temp, item.find(match)) + len(temp):]
                lst2.append(temp)
            lst = lst2
        ret_lst += lst

    return ret_lst


def _getDOMContent(html, name, match, ret):

    endstr = "</" + name  # + ">"

    start = html.find(match)
    end = html.find(endstr, start)
    pos = html.find("<" + name, start + 1 )

    while pos < end and pos != -1:  # Ignore too early </endstr> return
        tend = html.find(endstr, end + len(endstr))
        if tend != -1:
            end = tend
        pos = html.find("<" + name, pos + 1)

    if start == -1 and end == -1:
        result = ""
    elif start > -1 and end > -1:
        result = html[start + len(match):end]
    elif end > -1:
        result = html[:end]
    elif start > -1:
        result = html[start + len(match):]

    if ret:
        endstr = html[end:html.find(">", html.find(endstr)) + 1]
        result = match + result + endstr

    return result


def _getDOMAttributes(match, name, ret):

    lst = re.compile('<' + name + '.*?' + ret + '=([\'"].[^>]*?[\'"])>', re.M | re.S).findall(match)
    if len(lst) == 0:
        lst = re.compile('<' + name + '.*?' + ret + '=(.[^>]*?)>', re.M | re.S).findall(match)
    ret = []
    for tmp in lst:
        cont_char = tmp[0]
        if cont_char in "'\"":

            # Limit down to next variable.
            if tmp.find('=' + cont_char, tmp.find(cont_char, 1)) > -1:
                tmp = tmp[:tmp.find('=' + cont_char, tmp.find(cont_char, 1))]

            # Limit to the last quotation mark
            if tmp.rfind(cont_char, 1) > -1:
                tmp = tmp[1:tmp.rfind(cont_char)]
        else:
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
            lst = lst2
            lst2 = []
        else:
            test = list(range(len(lst)))
            test.reverse()
            for i in test:  # Delete anything missing from the next list.
                if not lst[i] in lst2:
                    del(lst[i])

    if len(lst) == 0 and attrs == {}:

        lst = re.compile('(<' + name + '>)', re.M | re.S).findall(item)
        if len(lst) == 0:
            lst = re.compile('(<' + name + ' .*?>)', re.M | re.S).findall(item)

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
        pattern = r'(<%s(?:\s[^>]*>|/?>))' % name
        this_list = re.findall(pattern, item, re.M | re.S | re.I)
    else:
        last_list = None
        for key, value in iter(attrs.items()):
            value_is_regex = isinstance(value, re_type)
            value_is_str = isinstance(value, str)
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


def dom_parser(html, name='', attrs=None, ret=False):
    if attrs is None:
        attrs = {}
    name = name.strip()
    if isinstance(html, str) or isinstance(html, DomMatch):
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
