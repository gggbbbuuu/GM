# -*- coding: utf-8 -*-
import re
import time

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


def get_links(tv_movie,original_title,season_n,episode_n,season,episode,show_original_year,id):
    global global_var,stop_all
    all_links=[]
    imdb_id=cache.get(get_imdb, 999,tv_movie,id,table='pages')
        
    
    added_season=''
    if tv_movie=='tv':
        tv_movie='series'
        added_season=':%s:%s'%(season,episode)
    
    url=f'https://torrentio.elfhosted.com/stream/{tv_movie}/{imdb_id}{added_season}.json'
    log.warning(url)
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        
        'priority': 'u=1, i',
        
        'sec-ch-ua': '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0',
    }
    x=get_html(url,headers=headers).json()
    
    for results in x['streams']:

            if stop_all==1:
                break
            nam=results['title'].split('💾')[0]
            size=results['title'].split('💾')[1]
            try:
                 o_size=size
                 
                 size=float(o_size.replace('GB','').replace('MB','').replace(",",'').strip())
                 if 'MB' in o_size:
                   size=size/1000
            except Exception as e:
                
                size=0
                    
            links=results['infoHash']
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
            
            
            if (size)<max_size:
               
                all_links.append((nam,lk,str(size),res))

                global_var=all_links
    return global_var