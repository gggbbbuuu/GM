# -*- coding: utf-8 -*-

import six, re, requests, json

def clear_Title(txt):
    txt = six.ensure_str(txt, errors='ignore')
    txt = re.sub('<.+?>', '', txt)
    txt = txt.replace('Δες το ', '').replace(' online', '')
    txt = txt.replace("&quot;", "\"").replace('()','').replace("&#038;", "&").replace('&#8211;',':').replace('\n',' ')
    txt = txt.replace("&amp;", "&").replace('&#8217;',"'").replace('&#039;',':').replace('&#;','\'')
    txt = txt.replace("&#38;", "&").replace('&#8221;','"').replace('&#8216;','"').replace('&#160;','')
    txt = txt.replace("&nbsp;", "").replace('&#8220;','"').replace('&#8216;','"').replace('\t',' ').replace('&#215;','x')
    txt = txt.replace("&#8230;", "…")
    return txt

def get_domains_url():
    try:
        urlcontent = requests.get('http://gknwizard.eu/repo/Builds/GKoBu/xmls/grs_domains.json', timeout=10)
        urlsdata = json.loads(urlcontent.text)
    except:
        urlsdata = {
                        "DADDYLIVE": "https://daddylive.sx/",
                        "AN1ME": "https://an1me.to/",
                        "GAMATO": "https://gamatotv.info/",
                        "GAMATOMOVIES": "https://gamatomovies1.gr/",
                        "TAINIOMANIA": "https://tainio-mania.online/",
                        "TENIES-ONLINE": "https://tenies-online1.gr/",
                        "TENIES-ONLINE BEST": "https://tenies-online.best/",
                        "XRYSOI": "https://xrysoi.pro/",
                        "GAMATO_TAG_STRING": "/tag/",
                        "GAMATO_MOVIE_PAGE": [6,11088],
                        "GAMATO_SHOWS_PAGE": [7,11016],
                        "GAMATO_CAT_PAGE": "29366"
                    }
    
    return urlsdata

