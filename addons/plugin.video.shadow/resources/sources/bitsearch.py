# -*- coding: utf-8 -*-
import re
import time

global global_var,stop_all#global
global_var=[]
stop_all=0
from  resources.modules.client import get_html
 
from resources.modules.general import clean_name,check_link,server_data,replaceHTMLCodes,domain_s,similar,all_colors,base_header,detect_quality_from_name,parse_size_to_gb
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
    
    # ====== PERFORMANCE: Cache settings before loops ======
    max_size = int(Addon.getSetting("size_limit"))
    debrid_select = Addon.getSetting('debrid_select')
    
    imdb_id=cache.get(get_imdb, 999,tv_movie,id,table='pages')
        

    
    if tv_movie=='movie':
        
        search_url=[((clean_name(original_title,1).replace(' ','%20')+'%20'+show_original_year)).lower()]
    else:
      
      if debrid_select=='0' :
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
        
        ur='https://bitsearch.eu/search?q=%s&category=1&subcat=2&page=%s'%(itt,page)
        
        
        y=get_html(ur,headers=headers,timeout=10).content()
        regex='<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md[^>]*?>(.+?)<div class="sm:hidden mt-4 flex space-x-2">.+?</div>\s*</div>'
        m=re.compile(regex,re.DOTALL).findall(y)
 
        for items in m:
            regex='<h3[^>]*?>\s*<a href="/torrent/[^"]+?"[^>]*?>(.+?)</a>.+?<i class="fas fa-download"></i>\s*<span>(.+?)</span>.+?href="(magnet:?[^"]+?)"'
            m2=re.compile(regex,re.DOTALL).findall(items)
            
            for nm,size,lk in m2:
                
          
                  
                if stop_all==1:
                    break
                nam=replaceHTMLCodes(nm.strip())
                
                # ====== PERFORMANCE: Use helper function for size parsing ======
                size = parse_size_to_gb(size)
                
                
                links=replaceHTMLCodes(lk.replace('&amp;','&'))
                
                # ====== PERFORMANCE: Use helper function for quality detection ======
                res = detect_quality_from_name(nam)
                
                
                if (size)<max_size:
                   
                    all_links.append((nam,links,str(size),res))

                    global_var=all_links
    return global_var