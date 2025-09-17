# -*- coding: utf-8 -*-
import re
import time
from  resources.modules.client import get_html
global global_var,stop_all#global
global_var=[]
stop_all=0


from resources.modules.general import clean_name,check_link,server_data,replaceHTMLCodes,domain_s,similar,all_colors,base_header
from  resources.modules import cache
try:
    from resources.modules.general import Addon
except:
  import Addon
type=['movie','tv','torrent']

import urllib,logging,base64,json
from resources.modules import log
try:
    que=urllib.quote_plus
    url_encode=urllib.urlencode
except:
    que=urllib.parse.quote_plus
    url_encode=urllib.parse.urlencode
def get_links(tv_movie,original_title,season_n,episode_n,season,episode,show_original_year,id):
    global global_var,stop_all

   
    
  
    
    
    all_links=[]
    if tv_movie=='movie':
     search_url=('%s %s'%(clean_name(original_title,1),show_original_year)).lower()
    else:
     search_url=('%s s%se%s'%(clean_name(original_title,1),season_n,episode_n)).lower()
    
   
    
    for page in range(1,4):
        
        

        
   
        
        
        
        
        y= get_html('https://solidtorrents.to/search?q=%s&page=%s'%(que(search_url),str(page)), headers=base_header, timeout=10).content()
        
        regex='<li class="card search-result my(.+?)</li>'
        mm=re.compile(regex,re.DOTALL).findall(y)
        for itt in mm:
            regex='data-token=".+?">(.+?)</a>.+?alt="Size" style=".+?">(.+?)<.+?a href="magnet(.+?)"'
            mm_in=re.compile(regex,re.DOTALL).findall(itt)
            for nm,size,lk in mm_in:
                if stop_all==1:
                    break
                link='magnet'+lk
                try:
                     o_size=size
                     
                     size=float(o_size.replace('GB','').replace('MB','').replace(",",'').strip())
                     if 'MB' in o_size:
                       size=size/1000
                except Exception as e:
                    
                    size=0
               
                title=nm
                if '4k' in title:
                          res='2160'
                elif '2160' in title:
                      res='2160'
                elif '1080' in title:
                      res='1080'
                elif '720' in title:
                      res='720'
                elif '480' in title:
                      res='480'
                elif '360' in title:
                      res='360'
                else:
                      res='HD'
                
                
               
                 
                max_size=int(Addon.getSetting("size_limit"))
          
                if size<max_size:
                  
                   all_links.append((title,link,str(size),res))
               
                   global_var=all_links
    return global_var
        
    