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
        

    
    if tv_movie=='movie':
        
        search_url=[((clean_name(original_title,1).replace(' ','%20')+'%20'+show_original_year)).lower()]
    else:
      
      if Addon.getSetting('debrid_select')=='0' :
        search_url=[clean_name(original_title,1).replace(' ','%20')+'%20s'+season_n+'e'+episode_n,clean_name(original_title,1).replace(' ','%20')+'%20s'+season_n,clean_name(original_title,1).replace(' ','%20')+'%20season%20'+season]
      else:
        search_url=[clean_name(original_title,1).replace(' ','%20')+'%20s'+season_n+'e'+episode_n]
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    }
    for page in range(1,4):
     for itt in search_url:
        
        ur='https://bitsearch.to/search?q=%s&category=1&subcat=2&page=%s'%(itt,page)
        
        y=get_html(ur,headers=headers,timeout=10).content()
        regex='li class="card search-result my(.+?)</li>'
        m=re.compile(regex,re.DOTALL).findall(y)
        for items in m:
            regex='data-token=".+?">(.+?)</a>.+?alt="Size" style=".+?">(.+?)</div>.+?href="magnet(.+?)"'
            m2=re.compile(regex,re.DOTALL).findall(items)
            for nm,size,lk in m2:
                
          
                  
                if stop_all==1:
                    break
                nam=nm
                try:
                     o_size=size
                     size=float(o_size.replace('GB','').replace('MB','').replace(",",'').strip())
                     if 'MB' in o_size:
                       size=size/1000
                except Exception as e:
                   
                    size=0
                
                
                links='magnet'+lk.replace('xt&#x3D;','xt=').replace('&amp;','&')
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
                   
                    all_links.append((nam,links,str(size),res))

                    global_var=all_links
    return global_var