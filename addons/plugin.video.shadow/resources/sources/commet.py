# -*- coding: utf-8 -*-
import re
import time
import base64
from json import dumps as jsdumps
global global_var,stop_all#global
global_var=[]
stop_all=0
from  resources.modules.client import get_html
 
from resources.modules.general import clean_name,check_link,server_data,replaceHTMLCodes,domain_s,similar,all_colors,base_header
from  resources.modules import cache
try:
    from resources.modules.general import Addon,get_imdb
except:
  import Addon
type=['movie','tv','torrent']

import urllib,logging,base64,json

from resources.modules import log

try:
    que=urllib.quote_plus
except:
    que=urllib.parse.quote_plus
color=all_colors[112]

def build_url(tv_movie,imdb,season,episode):
    if Addon.getSetting("debrid_use_rd")=='true':
        debrid_service = 'realdebrid'
        debrid_token=Addon.getSetting('rd.auth')
    elif Addon.getSetting("debrid_use_pm")=='true':
        debrid_service = 'premiumize'
        debrid_token=Addon.getSetting('premiumize.token')
    elif Addon.getSetting("debrid_use_ad")=='true':
        debrid_service = 'alldebrid'
        debrid_token=Addon.getSetting('alldebrid.token')
    base_link = 'https://comet.elfhosted.com'
    movieSearch_link = '/%s/stream/movie/%s.json'
    tvSearch_link = '/%s/stream/series/%s:%s:%s.json'
    
    
    params={"maxResultsPerResolution":0,"maxSize":0,"cachedOnly":True,"removeTrash":True,"resultFormat":["all"],"debridService":debrid_service,"debridApiKey":debrid_token,"debridStreamProxyPassword":"","languages":{"exclude":["multi"],"preferred":["multi"]},"resolutions":{},"options":{"remove_ranks_under":-10000000000,"allow_english_in_languages":False,"remove_unknown_languages":False}}
    
    params = base64.b64encode(jsdumps(params, separators=(',', ':')).encode('utf-8')).decode('utf-8')
    if tv_movie=='movie':
        url = '%s%s' % (base_link, movieSearch_link % (params, imdb))
    else:
        url = '%s%s' % (base_link, tvSearch_link % (params, imdb, season, episode))
    
    return url

def get_links(tv_movie,original_title,season_n,episode_n,season,episode,show_original_year,id):
    global global_var,stop_all
    all_links=[]
    imdb_id=cache.get(get_imdb, 999,tv_movie,id,table='pages')


    url=build_url(tv_movie,imdb_id,season_n,episode_n)
   
    log.warning(f'Comet URL: {url}')
    x=get_html(url,headers=base_header).json()
    
    if 'streams' not in x:
        return global_var
    for results in x['streams']:

            if stop_all==1:
                break
            if 'filename' in results['behaviorHints']:
                nam=results['behaviorHints']['filename']
            else:
                nam=results['description'].split('\n')[0].replace('📄','').strip()
            size=(float(results['behaviorHints']['videoSize'])/(1024*1024*1024))
            
            links=results['behaviorHints']['bingeGroup'].replace('comet|', '')
            lk='magnet:?xt=urn:btih:%s&dn=%s'%(links,que(original_title))
            if '4k' in nam:
                  res='2160'
            elif '2160' in nam:
                  res='2160'
            elif '1080' in nam:
                      res='1080'
            elif '720' in nam:
                  res='720'
            elif '480' in nam:
                  res='480'
            elif '360' in nam:
                  res='360'
            else:
                  res='HD'
            max_size=int(Addon.getSetting("size_limit"))
            
            log.warning(f'Size:{size},maxsize:{max_size}')
            if (size)<max_size:
               
                all_links.append((nam,lk,str(size),res))

                global_var=all_links
    return global_var