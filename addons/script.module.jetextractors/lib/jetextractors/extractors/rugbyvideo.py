# -*- coding: utf-8 -*-
"""RugbyVideo for JetExtractors, using reusable script.module.go."""
import os,sys,re
from urllib.parse import urljoin,urlparse
import xbmc,xbmcaddon
from bs4 import BeautifulSoup
from ..models import JetExtractor,JetItem,JetLink
from .sportsvideo import SportsVideo

if not getattr(SportsVideo,'_r24_exclusive',False):
    _available=SportsVideo.is_available
    def _other(self,link):
        return urlparse(getattr(link,'address','')).hostname!='rugby24.net' and _available(self,link)
    SportsVideo.is_available=_other
    SportsVideo._r24_exclusive=True

try:
    root=xbmcaddon.Addon('script.module.go').getAddonInfo('path')
    try:
        import xbmcvfs
        root=xbmcvfs.translatePath(root)
    except (ImportError,AttributeError): pass
    sys.path.insert(0,os.path.join(root,'lib'))
    from goclient import get
except Exception as exc:
    get=None
    _import_error=str(exc)

def _html(url):
    if not get: raise RuntimeError('Install script.module.go: '+_import_error)
    error='No response'
    for p in ('android','chrome133'):
        r=get(url,profile=p,timeout=25)
        if r.status_code==200 and r.text.strip() and not r.cf_mitigated and 'just a moment' not in r.text[:2000].lower():
            return r.text
        error=r.error or 'HTTP {} {}'.format(r.status_code,r.cf_mitigated)
    raise RuntimeError(error)

class RugbyVideo(JetExtractor):
    name='RugbyVideo'
    domains=['rugby24.net']
    base='https://rugby24.net/'

    def get_items(self,params=None,progress=None):
        items=[]
        if self.progress_init(progress,items) or (params or {}).get('notice'): return items
        try: page=max(1,int((params or {}).get('page') or 1))
        except (ValueError,TypeError): page=1
        url=self.base+('' if page==1 else '?page{}'.format(page))
        try: soup=BeautifulSoup(_html(url),'html.parser')
        except Exception as exc:
            xbmc.log('[RugbyVideo] '+str(exc),xbmc.LOGERROR)
            return [JetItem('RugbyVideo: '+str(exc),links=[],params={'notice':True})]
        seen=set()
        for card in soup.select('.short_item.block_elem'):
            tag=card.select_one('h3 a[href]')
            if not tag: continue
            link=urljoin(url,tag['href'])
            if urlparse(link).hostname!='rugby24.net' or link in seen: continue
            title=re.sub(r'\s+',' ',tag.get_text(' ',strip=True))
            title=re.sub(r'^Full Game Replay\s*[-:]?\s*','',title,flags=re.I)
            if not title: continue
            if self.progress_update(progress,title): return items
            seen.add(link)
            img=card.select_one('.poster img') or card.select_one('img')
            pic=(img.get('data-src') or img.get('data-lazy-src') or img.get('src')) if img else ''
            items.append(JetItem(title,links=[JetLink(link,links=True,extractor='RugbyVideo')],icon=urljoin(url,pic) if pic else ''))
        for tag in soup.select('.paging-wrapper-bottom a[href],a.swchItem[href]'):
            if re.search(r'(?:\?|&)page{}(?:=|&|$)'.format(page+1),urljoin(url,tag['href'])):
                items.append(JetItem('Page {}'.format(page+1),links=[],params={'page':page+1}))
                break
        return items

    def get_links(self,url):
        address=url.address
        if urlparse(address).hostname!='rugby24.net': return []
        try: soup=BeautifulSoup(_html(address),'html.parser')
        except Exception as exc:
            xbmc.log('[RugbyVideo] Replay: '+str(exc),xbmc.LOGERROR)
            return []
        links=[]
        for tag in (soup.select_one('.fullstory') or soup).select('iframe[src],iframe[data-src],a.su-button[href]'):
            link=urljoin(address,tag.get('data-src') or tag.get('src') or tag.get('href') or '')
            if urlparse(link).scheme not in ('http','https') or any(a.address==link for a in links): continue
            links.append(JetLink(link,name='Server {} - {}'.format(len(links)+1,urlparse(link).hostname),resolveurl=True))
        return links
