import requests, re
from ..util import m3u8_src
from urllib.parse import urlparse

# Updated UA
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

ad_hosts = ""

def find_iframes(url, prev_url = "", links = [], checked = [], headers = {}):
    from .. import extractor
    extractors = extractor.get_extractors()
    try:
        links = links
        checked = checked
        # Merge passed headers with UA
        req_headers = {"User-Agent": user_agent, "Referer": prev_url}
        req_headers.update(headers)
        r = requests.get(url, allow_redirects=True, timeout=7, headers=req_headers)
        if r.status_code == 200:
            urls = re.findall('i?frame.+?src=[\"\']?([^\"\' ]+)', r.text, flags=re.IGNORECASE)
            urls = __customUrls(r.text, url, urls)
            scan = m3u8_src.scan_page(url, html=r.text)
            if scan: return [scan]
            for u in urls:
                if urlparse(u).netloc == '':
                    if u.startswith('/'): u = 'http://' + urlparse(url).netloc + '/' + u
                    else: u = 'http://' + urlparse(url).netloc + '/'.join(urlparse(url).path.split('/')[:-1]) +  '/' + u
                if urlparse(u).scheme == '': u = 'http://' + u.replace('//','')

                u = re.sub(r'\n+', '', u)
                u = re.sub(r'\r+', '', u)
                
                domain = urlparse(u).netloc
                if not isAd(u) and u not in checked and __checkUrl(u) and u not in links and len(links)<15:
                    if u.startswith("https://href.li/?"): u = u.replace("https://href.li/?", "")
                    # Skip intermediate PHP files from streams.center - only accept actual m3u8
                    if "streams.center" in domain or "streamscenter" in domain or "streamcenter" in domain:
                        if ".m3u8" not in u:
                            # Don't add PHP intermediate files, but do recurse to find the actual stream
                            links += find_iframes(u, url, links, checked, headers)
                            checked.append(u)
                            continue
                    for module in extractors:
                        if domain in module.domains or ".m3u8" in u:
                            if ".m3u8" in u or "wigistream" in u: u += "|Referer=%s&User-Agent=%s" % (url.replace("&", "_"), user_agent)
                            links.append(u)
                    # Recurse with headers
                    links += find_iframes(u, url, links, checked, headers)
                    checked.append(u)
            return list(set(links))
        return []
    except Exception as e:
        return []

# ... (rest unchanged: isAd, __checkUrl, __customUrls)

def isAd(host):
    global ad_hosts
    if ad_hosts == "":
        ad_hosts = requests.get('https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts').text
    h = urlparse(host).netloc
    return (h in ad_hosts) or "/ad" in host

def __checkUrl(url):
		blacklist = ['chatango', 'adserv', 'live_chat', 'ad4', 'cloudfront', 'image/svg', 'getbanner.php','/ads', 'ads.', 'adskeeper', '.js', '.jpg', '.png', '/adself.', 'min.js', 'mail.ru', "/http", "googleusercontent"]
		return not any(w in url for w in blacklist)

def __customUrls(r, ref, urls):
    fid = re.findall('id\s*=\s*[\"\']([^\"\']+).+?jokersplayer.+?\.js', r)
    tiny = re.findall('href\s*=\s*[\"\']([^\"\']+).+?class\s*=\s*[\"\']btn\s*btn\-secondary', r)
    unes = re.findall('=\s*[\"\']([^\"\']+)[\"\']+[^\"\']+unescape', r)
    multiline = re.findall('i?frame\s*.+?src=[\"\']?([^\"\']+)', r, flags=re.IGNORECASE | re.DOTALL)
    telerium = re.findall('id\s*=\s*[\"\']([^\"\']+).+?embed.telerium.+?\.js', r)
    url_in_url = bool(re.search('streamlink\.slice\(4\)', r))
    us = []
    if len(fid) > 0:
        u = 'http://www.jokersplayer.xyz/embed.php?u=' + fid[0]
        us.append(u)

    if len(telerium) > 0:
        u = 'http://telerium.club/embed/' + telerium[0] +'.html'
        us.append(u)

    if len(tiny) > 0:
        urls.append(tiny[0])

    if len(unes) > 0:
        u = unes[0].replace('@', '%')
        from urllib.parse import unquote
        html = unquote(u).decode('utf8')
        try:
            u = re.findall('i?frame\s*.+?src=[\"\']?([^\"\']+)', html, re.IGNORECASE)[0]
            us.append(u)
        except:
            pass
    if len(multiline)>0:

        for u in multiline:
            us.append(u)
    if url_in_url:
        u = re.findall('\?.{3}([^$]+)', ref)[0]
        us.append(u)
    for u in us:
        if not isAd(u) and __checkUrl(u) and u not in urls:
            urls.append(u)
    return urls