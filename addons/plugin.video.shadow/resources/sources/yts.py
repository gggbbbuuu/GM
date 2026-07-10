# -*- coding: utf-8 -*-
import re
import time
from  resources.modules.client import get_html
global global_var,stop_all#global
global_var=[]
stop_all=0

 
from resources.modules.general import clean_name,check_link,server_data,replaceHTMLCodes,domain_s,similar,all_colors,base_header,parse_size_to_gb
from  resources.modules import cache
try:
    from resources.modules.general import Addon
except:
  import Addon
type=['movie','torrent']

import urllib,logging,base64,json

def get_links(tv_movie,original_title,season_n,episode_n,season,episode,show_original_year,id):
    global global_var,stop_all
    
    # ====== PERFORMANCE: Cache max_size before loop ======
    max_size = int(Addon.getSetting("size_limit"))
    
    try:
        que=urllib.quote_plus
    except:
        que=urllib.parse.quote_plus
    
    if tv_movie=='movie':
      search_url=clean_name(original_title,1).replace(' ','%20')+'%20'
      s_type='Movies'
      type='207'
      type2='201'
    else:
      return []
      
    
    
    all_links=[]
    
    all_l=[]
    idd_table=['3','7']
    if 1:
      
        
            
        x=get_html('https://yts.bz/api/v2/list_movies.json?query_term=%s&page=1&limit=300&order_by=desc&sort_by=rating'%(search_url),headers=base_header,timeout=10,verify=False).json()
        if not isinstance(x, dict):
          return global_var
        movies = x.get('data', {}).get('movies')
        if movies is None:
          log.warning('YTS unexpected payload: %s' % str(x)[:300])
          return global_var
        
        
   
        
     
      
       
        
                
        
        for items in movies:
                        title=items['slug'].replace('-','.')
                        for te in items['torrents']:
                         hash=te['hash']
                         link='magnet:?xt=urn:btih:%s&dn=%s'%(hash,que(title))
                         
                         size=te['size']
                         res=te['quality'].replace('p','')
                        
                         
                         
                     
                         
                        
                         o_link=link
                        
                         # ====== PERFORMANCE: Use helper function for size parsing ======
                         size = parse_size_to_gb(size)
                         max_size=int(Addon.getSetting("size_limit"))
                        
                         if size<max_size:
                         
                           all_links.append((title,link,str(size),res))
                       
                           global_var=all_links
                         
    
    return global_var
        
    