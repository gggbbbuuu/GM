# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from tulip.compat import urlencode
from random import choice


BRAVE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.38 Safari/537.36 Brave/75" # Windows
CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"  # Windows
EDGE = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1474.0"
FIREFOX = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0"
FIREFOX_LINUX = "Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0"
TIZEN = 'Mozilla/5.0 (Linux; U; Tizen 2.0; en-us) AppleWebKit/537.1 (KHTML, like Gecko) Mobile TizenBrowser/2.0'
IE_6 = "Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1)"
IE_11 = "Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko"
IPAD = "Mozilla/5.0 (iPad; CPU OS 11_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.0 Tablet/15E148 Safari/604.1"
IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Mobile/15E148 Snapchat/10.77.5.59 (like Safari/604.1)'
OPERA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 OPR/92.0.0.0 (Edition Yx 05)"
SAFARI = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
PY_URLLIB_2 = "Python-urllib/2.7"
PY_URLLIB_3 = "Python-urllib/3.10"

OPERA_MINI = 'Opera/9.80 (Android; Opera Mini/7.29530/27.1407; U; en) Presto/2.8.119 Version/11.10'
MIUI = 'Mozilla/5.0 (Linux; U; Android 7.0; en-us; MI 5 Build/NRD90M) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/53.0.2785.146 Mobile Safari/537.36 XiaoMi/MiuiBrowser/9.0.3'
ANDROID = "Mozilla/5.0 (Linux; Android 10; ZenFone Max Pro M1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36"
WEBVIEW = 'Mozilla/5.0 (Linux; Android 11; moto g stylus 5G Build/RRE31.Q2-11-52-4; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/98.0.4758.87 Mobile Safari/537.36'
PUFFIN = 'Mozilla/5.0 (Linux; Android 5.1.1; SM-N750K Build/LMY47X; ko-kr) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Mobile Safari/537.36 Puffin/6.0.8.15804AP'
SAMSUNG = 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G986B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/15.0 Chrome/90.0.4430.210 Mobile Safari/537.36'


def randomagent():

    agents = [BRAVE, CHROME, EDGE, FIREFOX, FIREFOX_LINUX, SAFARI, IE_11, TIZEN]

    return choice(agents)


def agent():

    return 'Mozilla/5.0 CK={} (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko'


def mobile_agent():

    return 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G531M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.93 Mobile Safari/537.36'


def random_mobile_agent():

    agents = [OPERA_MINI, ANDROID, PUFFIN, WEBVIEW, MIUI, SAMSUNG]

    return choice(agents)


def ios_agent():

    return 'Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25'


def spoofer(headers=None, _agent=True, age_str=None, referer=False, ref_str='', url=None):

    if age_str is None:
        age_str = randomagent()

    pipe = '|'

    if not headers:
        headers = {}

    if _agent and age_str and not headers:
        headers.update({'User-Agent': age_str})

    if referer and ref_str:
        headers.update({'Referer': ref_str})

    if headers:
        string = pipe + urlencode(headers)
        if url:
            url += string
            return url
        else:
            return string
    else:
        return ''
