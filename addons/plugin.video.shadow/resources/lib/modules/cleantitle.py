# -*- coding: utf-8 -*-

import re
import unicodedata
from string import printable

from six import ensure_str, ensure_text, PY2
from six.moves import urllib_parse

from resources.lib.modules import control
andToggle = control.setting('sourcefilter.and') or 'false'


def normalize(title):
    try:
        if PY2:
            try:
                return title.decode('ascii').encode("utf-8")
            except:
                pass
            return str(''.join(c for c in unicodedata.normalize('NFKD', title.decode('utf-8')) if c in printable))
        return u''.join(c for c in unicodedata.normalize('NFKD', ensure_text(title)) if c in printable)
    except:
        return title


def get_title(title):
    if title is None:
        return
    try:
        title = ensure_str(title)
    except:
        pass
    title = urllib_parse.unquote(title)
    title = re.sub('[^A-Za-z0-9 ]+', ' ', title)
    title = re.sub(' {2,}', ' ', title)
    title = title.strip().lower()
    return title


def get(title):
    if title is None:
        return
    try:
        title = ensure_str(title)
    except:
        pass
    title = re.sub(r'&#(\d+);', '', title)
    title = re.sub(r'(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title)
    title = title.replace(r'&quot;', '\"').replace(r'&amp;', '&').replace(r'–', '-').replace(r'!', '')
    title = re.sub(r'\n|([[].+?[]])|([(].+?[)])|\s(vs|v[.])\s|(:|;|-|–|"|,|\'|\_|\.|\?)|\s', '', title)
    return title.lower()


def getsearch(title):
    if title is None:
        return
    try:
        title = ensure_str(title)
    except:
        pass
    title = title.lower()
    title = re.sub('&#(\d+);', '', title)
    title = re.sub('(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title)
    title = title.replace('&quot;', '\"').replace('&amp;', '&').replace('–', '-')
    title = re.sub('\\\|/|-|–|:|;|!|\*|\?|"|\'|<|>|\|', '', title).lower()
    return title


def geturl(title):
    if title is None:
        return
    try:
        title = ensure_str(title)
    except:
        pass
    title = title.lower()
    title = title.rstrip()
    try:
        title = title.translate(None, ':*?"\'\.<>|&!,')
    except:
        title = title.translate(str.maketrans('', '', ':*?"\'\.<>|&!,'))
    title = title.replace('/', '-')
    title = title.replace(' ', '-')
    title = title.replace('--', '-')
    title = title.replace('–', '-')
    title = title.replace('!', '')
    return title


def get_under(title):
    if title == None:
        return
    title = getsearch(title)
    title = title.replace(' ', '_')
    title = title.replace('__', '_')
    return title


def get_dash(title):
    if title == None:
        return
    title = getsearch(title)
    title = title.replace(' ', '-')
    title = title.replace('--', '-')
    return title


def get_plus(title):
    if title == None:
        return
    title = getsearch(title)
    title = title.replace(' ', '+')
    title = title.replace('++', '+')
    return title


def get_utf8(title):
    if title == None:
        return
    title = getsearch(title)
    title = title.replace(' ', '%20')
    title = title.replace('%20%20', '%20')
    return title


def match_alias(title, aliases):
    try:
        for alias in aliases:
            if get(title) == get(alias['title']):
                return True
        return False
    except:
        return False


def match_year(item, year, premiered=None):
    try:
        if premiered == None:
            check1 = [(int(year))]
            check2 = [(int(year)-1), (int(year)), (int(year)+1)]
        else:
            check1 = [(int(year)), (int(premiered))]
            check2 = [(int(year)-1), (int(year)), (int(year)+1), (int(premiered)-1), (int(premiered)), (int(premiered)+1)]
        if any(str(y) in str(item) for y in check1):
            return True
        if any(str(y) in str(item) for y in check2):
            return True
        return False
    except:
        return False


def scene_title(title, imdb, year):
    title = normalize(title)
    try:
        title = ensure_str(title)
    except:
        pass
    title = title.replace('&', 'AAANNNDDD').replace('-', ' ').replace('–', ' ').replace('/', ' ').replace('*', ' ').replace('.', ' ')
    title = re.sub('[^A-Za-z0-9 ]+', '', title)
    title = re.sub(' {2,}', ' ', title).strip()
    if andToggle == 'true':
        title = title.replace('AAANNNDDD', '&')
    else:
        title = title.replace('AAANNNDDD', 'and')
    if title.startswith('Birdman or') and year == '2014':
        title = 'Birdman'
    if title == 'Birds of Prey and the Fantabulous Emancipation of One Harley Quinn' and year == '2020':
        title = 'Birds of Prey'
    if title == "Roald Dahls The Witches" and year == '2020':
        title = 'The Witches'
    return title, imdb, year


def scene_tvtitle(title, imdb, year, season, episode):
    title = normalize(title)
    try:
        title = ensure_str(title)
    except:
        pass
    title = title.replace('&', 'AAANNNDDD').replace('-', ' ').replace('–', ' ').replace('/', ' ').replace('*', ' ').replace('.', ' ')
    title = re.sub('[^A-Za-z0-9 ]+', '', title)
    title = re.sub(' {2,}', ' ', title).strip()
    if andToggle == 'true':
        title = title.replace('AAANNNDDD', '&')
    else:
        title = title.replace('AAANNNDDD', 'and')
    if title in ['The Haunting', 'The Haunting of Bly Manor', 'The Haunting of Hill House'] and year == '2018':
        if season == '1':
            title = 'The Haunting of Hill House'
        elif season == '2':
            title = 'The Haunting of Bly Manor'
            year = '2020'
            season = '1'
    if title in ['Cosmos', 'Cosmos A Spacetime Odyssey', 'Cosmos Possible Worlds'] and year == '2014':
        if season == '1':
            title = 'Cosmos A Spacetime Odyssey'
        elif season == '2':
            title = 'Cosmos Possible Worlds'
            year = '2020'
            season = '1'
    if 'Special Victims Unit' in title:
        title = title.replace('Special Victims Unit', 'SVU')
    if title == 'Cobra Kai' and year == '1984':
        year = '2018'
    if title == 'The End of the F ing World':
        title = 'The End of the Fucking World'
    if title == 'M A S H':
        title = 'MASH'
    if title == 'Bleach' and year == '2004':
        if season == '2':
            title = 'Bleach: Thousand-Year Blood War'
            #title = 'Bleach: Sennen Kessen-hen'
            year = '2022'
            season = '1'
            imdb = 'tt14986406'

    #if title == ('King and Maxwell' or 'King & Maxwell'):
        #title = 'King & Maxwell'

    #if title == 'House': #Isnt really needed but gives more accurate results this way. might just add it to the scrapers it works on.
        #title = 'House M.D.'
    return title, imdb, year, season, episode


