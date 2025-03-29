# -*- coding: utf-8 -*-

import re
import requests

import simplejson as json
from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import client
from resources.lib.modules import control
from resources.lib.modules import jsunpack
from resources.lib.modules import source_utils
from resources.lib.modules import log_utils


"""Example...

from resources.lib.modules import scrape_sources
for source in scrape_sources.process(url, hostDict):
    sources.append(source)

scrape_sources.rescrape(url)

scrape_sources.prepare_link(url)


"""


def prepare_link(url):
    if not url:
        return
    url = "https:" + url if url.startswith('//') else url
    if '2embed.ru' in url:
        url = url.replace('2embed.ru', '2embed.to')
    if 'cloudvid.co' in url:
        url = url.replace('cloudvid.co', 'cloudvideo.tv')
    if 'dood.pm' in url:
        url = url.replace('dood.pm', 'doodstream.com')
    if 'dood.cx' in url:
        url = url.replace('dood.cx', 'doodstream.com')
    if 'dood.to' in url:
        url = url.replace('dood.to', 'doodstream.com')
    if 'dood.so' in url:
        url = url.replace('dood.so', 'doodstream.com')
    if 'eplayvid.com' in url:
        url = url.replace('eplayvid.com', 'eplayvid.net')
    if 'gomostream.com' in url:
        url = url.replace('gomostream.com', 'gomo.to')
    if 'sendit.cloud' in url:
        url = url.replace('sendit.cloud', 'send.cm')
    if 'vidcloud.icu' in url:
        url = url.replace('vidcloud.icu', 'vidembed.io')
    if 'vidcloud9.com' in url:
        url = url.replace('vidcloud9.com', 'vidembed.io')
    if 'vidembed.cc' in url:
        url = url.replace('vidembed.cc', 'vidembed.io')
    if 'vidembed.io' in url:
        url = url.replace('vidembed.io', 'membed.net')
    if 'vidnext.net' in url:
        url = url.replace('vidnext.net', 'vidembed.me')
    if 'vidembed.me' in url:
        url = url.replace('vidembed.me', 'membed.net')
    if 'vidoza.net' in url:
        url = url.replace('vidoza.net', 'vidoza.co')
    #log_utils.log('scrape_sources - prepare_link link: ' + str(url))
    # this log line should log atleast 90% of the source links when used. altho its gonna have dupes and links from before and after various process steps.
    return url


def rescrape(url): # unused old code saved.
    try:
        html = client.scrapePage(url).text
        link = re.findall(r'(?:file|source)(?:\:)\s*(?:\"|\')(.+?)(?:\"|\')', html)[0]
        return link
    except:
        #log_utils.log('rescrape', 1)
        return url


def process(hostDict, link, host=None, info=None):
    sources = []
    try:
        if not link:
            return sources
        link = prepare_link(link)
        host = link if host == None else host
        info = link if info == None else info
        #if 'google' in link:
            #link = googlestream.googlepass(link)
        if 'linkbin.me' in host:
            for source in linkbin(link, hostDict, info=info):
                sources.append(source)
        elif any(i in host for i in ['gomo.to', 'gomostream.com', 'gomoplayer.com']):
            for source in gomo(link, hostDict, info=info):
                sources.append(source)
        elif any(i in host for i in ['database.gdriveplayer.us', 'databasegdriveplayer.co', 'series.databasegdriveplayer.co']):
            for source in gdriveplayer(link, hostDict, info=info):
                sources.append(source)
        elif 'vidlink.org' in host:
            for source in vidlink(link, hostDict, info=info):
                sources.append(source)
        elif any(i in host for i in ['goload.pro', 'goload.io', 'membed.net', 'vidembed.me', 'vidembed.io', 'vidembed.cc', 'vidcloud9.com']):
            for source in vidembed(link, hostDict, info=info):
                sources.append(source)
        elif 'voxzer.org' in host:
            for source in voxzer(link, hostDict, info=info):
                sources.append(source)
        elif 'ronemo.com' in host:
            for source in ronemo(link, hostDict, info=info):
                sources.append(source)
        elif any(i in host for i in ['2embed.ru', '2embed.to']):
            for source in twoembed(link, hostDict, info=info):
                sources.append(source)
        else:
            valid, host = source_utils.is_host_valid(host, hostDict)
            if valid:
                quality, info = source_utils.get_release_quality(link, info)
                sources.append({'source': host, 'quality': quality, 'info': info, 'url': link, 'direct': False})
        return sources
    except Exception:
        #log_utils.log('process', 1)
        return sources


def linkbin(link, hostDict, info=None):
    sources = []
    try:
        html = client.scrapePage(link).text
        urls = re.findall('<li class="signle-link"><a href="(.+?)" target="_blank">', html)
        for url in urls:
            url = prepare_link(url)
            valid, host = source_utils.is_host_valid(url, hostDict)
            if valid:
                quality, info = source_utils.get_release_quality(url, info)
                sources.append({'source': host, 'quality': quality, 'info': info, 'url': url, 'direct': False})
        return sources
    except Exception:
        #log_utils.log('linkbin', 1)
        return sources


def gomo(link, hostDict, info=None):
    sources = []
    try:
        domain = re.findall('(?://|\.)(gomo\.to|gomostream\.com|gomoplayer\.com)/', link)[0]
        gomo_link = 'https://%s/decoding_v3.php' % domain
        result = client.request(link, timeout='5')
        tc = re.compile('tc = \'(.+?)\';').findall(result)[0]
        if (tc):
            token = re.compile('"_token": "(.+?)",').findall(result)[0]
            post = {'tokenCode': tc, '_token': token}
            def tsd(tokenCode):
                _13x48X = tokenCode
                _71Wxx199 = _13x48X[4:18][::-1]
                return _71Wxx199 + "18" + "432782"
            headers = {'Host': domain, 'Referer': link, 'User-Agent': client.UserAgent, 'x-token': tsd(tc)}
            urls = client.request(gomo_link, XHR=True, post=post, headers=headers, output='json', timeout='5')
            for url in urls:
                if not url:
                    continue
                url = prepare_link(url)
                headers = {'User-Agent': client.UserAgent, 'Referer': url}
                if 'gomo.to' in url:
                    url = client.request(url, headers=headers, output='geturl', timeout='5')
                    if not url:
                        continue
                    if 'gomoplayer.com' in url:
                        html = client.request(url, headers=headers, timeout='5')
                        unpacked = client.unpacked(html)
                        links = re.compile('file:"(.+?)"').findall(unpacked)
                        for link in links:
                            if '/srt/' in link:
                                continue
                            quality, info = source_utils.get_release_quality(link, info)
                            link += '|%s' % urlencode({'Referer': url})
                            sources.append({'source': 'gomoplayer', 'quality': quality, 'info': info, 'url': link, 'direct': True})
                    elif any(i in url for i in ['database.gdriveplayer.us', 'databasegdriveplayer.co', 'series.databasegdriveplayer.co']):
                        for source in gdriveplayer(url, hostDict):
                            sources.append(source)
                    else:
                        valid, host = source_utils.checkHost(url, hostDict)
                        quality, info = source_utils.get_release_quality(url, info)
                        sources.append({'source': host, 'quality': quality, 'url': url, 'info': info, 'direct': False})
                        #sources.append({'source': 'gomo', 'quality': 'SD', 'url': url, 'direct': True})
                else:
                    valid, host = source_utils.checkHost(url, hostDict)
                    if valid:
                        quality, info = source_utils.get_release_quality(url, info)
                        sources.append({'source': host, 'quality': quality, 'url': url, 'info': info, 'direct': False})
        return sources
    except Exception:
        #log_utils.log('gomo', 1)
        return sources


def gdriveplayer(link, hostDict, info=None):
    sources = []
    try:
        html = client.scrapePage(link).text
        servers = client.parseDOM(html, 'ul', attrs={'class': 'list-server-items'})[0]
        urls = client.parseDOM(servers, 'a', ret='href')
        for url in urls:
            if not url or url.startswith('/player.php'):
                continue
            url = prepare_link(url)
            valid, host = source_utils.is_host_valid(url, hostDict)
            if valid:
                quality, info = source_utils.get_release_quality(url, info)
                sources.append({'source': host, 'quality': quality, 'info': info, 'url': url, 'direct': False})
        return sources
    except Exception:
        #log_utils.log('gdriveplayer', 1)
        return sources


def vidembed(link, hostDict, info=None):
    sources = []
    try:
        try:
            html = client.scrapePage(link).text
            urls = client.parseDOM(html, 'li', ret='data-video')
            if urls:
                for url in urls:
                    url = prepare_link(url)
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        quality, info = source_utils.get_release_quality(url, info)
                        sources.append({'source': host, 'quality': quality, 'info': info, 'url': url, 'direct': False})
        except:
            pass
        valid, host = source_utils.is_host_valid(link, hostDict)
        if valid:
            quality, info = source_utils.get_release_quality(link, info)
            sources.append({'source': host, 'quality': quality, 'info': info, 'url': link, 'direct': False})
        return sources
    except Exception:
        #log_utils.log('vidembed', 1)
        return sources


def vidlink(link, hostDict, info=None):
    sources = []
    try:
        return sources # site for update_views bit needs cfscrape so the links are trash.
        # return sources is added to cock block the urls from being seen lol.
        postID = link.split('/embed/')[1]
        post_link = 'https://vidlink.org/embed/update_views'
        headers = {'User-Agent': client.UserAgent, 'Referer': link}
        ihtml = client.request(post_link, post={'postID': postID}, headers=headers, XHR=True)
        log_utils.log('Scraper Testing ihtml: \n' + repr(ihtml))
        if ihtml:
            linkcode = client.unpacked(ihtml)
            linkcode = linkcode.replace('\\', '')
            links = re.findall(r'var file1="(.+?)"', linkcode)[0]
            stream_link = links.split('/pl/')[0]
            headers = {'Referer': 'https://vidlink.org/', 'User-Agent': client.UserAgent}
            response = client.request(links, headers=headers)
            urls = re.findall(r'[A-Z]{10}=\d+x(\d+)\W[A-Z]+=\"\w+\"\s+\/(.+?)\.', response)
            if urls:
                for qual, url in urls:
                    url = stream_link + '/' + url + '.m3u8'
                    qual = qual + ' ' + info if not info == None else qual
                    #log_utils.log('scrape_sources - process vidlink link: ' + str(url))
                    valid, host = source_utils.is_host_valid(url, hostDict)
                    if valid:
                        quality, info = source_utils.get_release_quality(qual, url)
                        sources.append({'source': host, 'quality': quality, 'info': info, 'url': url, 'direct': False})
        return sources
    except Exception:
        #log_utils.log('vidlink', 1)
        return sources


def get_recaptcha():
    response = requests.get(
        "https://recaptcha.harp.workers.dev/?anchor=https%3A%2F%2Fwww.google.com%2Frecaptcha%2Fapi2%2Fanchor%3Far%3D1%26k%3D6Lf2aYsgAAAAAFvU3-ybajmezOYy87U4fcEpWS4C%26co%3DaHR0cHM6Ly93d3cuMmVtYmVkLnRvOjQ0Mw..%26hl%3Den%26v%3DPRMRaAwB3KlylGQR57Dyk-pF%26size%3Dinvisible%26cb%3D7rsdercrealf&reload=https%3A%2F%2Fwww.google.com%2Frecaptcha%2Fapi2%2Freload%3Fk%3D6Lf2aYsgAAAAAFvU3-ybajmezOYy87U4fcEpWS4C"
    )
    return response.json()["rresp"]


def twoembed(link, hostDict, info=None):
    sources = []
    try:
        token = get_recaptcha()
        headers = {'User-Agent': client.UserAgent, 'Referer': 'https://www.2embed.to/'}
        r = requests.get(link, headers=headers).text
        items = client.parseDOM(r, 'a', ret='data-id')
        for item in items:
            try:
                stream = requests.get("https://www.2embed.to/ajax/embed/play", params={"id": item, "_token": token}, headers=headers).json()
                url = stream['link']
                if 'vidcloud.pro' in url:
                    r = client.request(url, headers={'User-Agent': client.UserAgent, 'Referer': url})
                    r = re.findall('sources = \[{"file":"(.+?)","type"', r)[0]
                    url = r.replace('\\', '')
                url = prepare_link(url)
                valid, host = source_utils.is_host_valid(url, hostDict)
                #if valid:
                quality, info = source_utils.get_release_quality(url, info)
                sources.append({'source': host, 'quality': quality, 'info': info, 'url': url, 'direct': False})
            except:
                #log_utils.log('twoembed', 1)
                pass
        return sources
    except Exception:
        #log_utils.log('twoembed', 1)
        return sources


def ronemo(link, hostDict, info=None):
    sources = []
    try:
        html = client.scrapePage(link).text
        url = re.findall('"link":"(.+?)",', html)[0]
        valid, host = source_utils.is_host_valid(url, hostDict)
        quality, info = source_utils.get_release_quality(url, info)
        url += '|%s' % urlencode({'Referer': link})
        sources.append({'source': host, 'quality': quality, 'info': info, 'url': url, 'direct': True})
        return sources
    except Exception:
        #log_utils.log('ronemo', 1)
        return sources


def voxzer(link, hostDict, info=None):
    sources = []
    try:
        link = link.replace('/view/', '/list/')
        html = client.scrapePage(link).json()
        url = html['link']
        valid, host = source_utils.is_host_valid(url, hostDict)
        quality, info = source_utils.get_release_quality(url, info)
        url += '|%s' % urlencode({'Referer': link})
        sources.append({'source': host, 'quality': quality, 'info': info, 'url': url, 'direct': True})
        return sources
    except Exception:
        #log_utils.log('voxzer', 1)
        return sources


