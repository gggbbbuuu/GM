# -*- coding: utf-8 -*-
import re
import time
from  resources.modules.client import get_html
global global_var,stop_all#global
global_var=[]
stop_all=0
from resources.modules import log
 
from resources.modules.general import clean_name,check_link,server_data,replaceHTMLCodes,domain_s,similar,all_colors,base_header,detect_quality_from_name,parse_size_to_gb
from  resources.modules import cache
try:
    from resources.modules.general import Addon
except:
  import Addon
type=['movie']

import urllib,logging,base64,json
import concurrent.futures
from concurrent.futures import wait
global all_links
all_links=[]

# ====== PERFORMANCE: Cache max_size globally for thread function ======
global max_size_cached
max_size_cached = 40  # Default, will be set in get_links

def trd_data(lk,nm,size):
   
   global all_links,global_var
   try:
   
    y=get_html(lk,headers=base_header,timeout=10,verify=False).content()
    
                
                
    regex='href="magnet(.+?)"'
    m2=re.compile(regex,re.DOTALL).findall(y)
    
    title=nm
    
    # ====== PERFORMANCE: Use helper function for quality detection ======
    res = detect_quality_from_name(title)
    
    # ====== PERFORMANCE: Use helper function for size parsing ======
    size = parse_size_to_gb(size)



              
      
    # ====== PERFORMANCE: Use cached max_size ======
    if size<max_size_cached:
       
       all_links.append((title,'magnet'+m2[0],str(size),res))
   
       global_var=all_links
   except Exception as e:
       log.warning('Error 1337x:'+str(e))
def get_links(tv_movie,original_title,season_n,episode_n,season,episode,show_original_year,id):
    global global_var,stop_all,all_links,max_size_cached
    
    # ====== PERFORMANCE: Cache settings before loops ======
    max_size_cached = int(Addon.getSetting("size_limit"))
    debrid_select = Addon.getSetting('debrid_select')
  
    if tv_movie=='movie':
        search_url=[clean_name(original_title,1).replace(' ','%20')]
    else:
        
        if debrid_select=='0' :
                
            search_url=[clean_name(original_title,1).replace(' ','%20')+'%20'+'S'+season_n,clean_name(original_title,1).replace(' ','%20')+'%20'+'s'+season_n+'e'+episode_n,clean_name(original_title,1).replace(' ','%20')+'%20'+'season '+season]
        else:
            search_url=[clean_name(original_title,1).replace(' ','%20')+'%20s{0}e{1}'.format(season_n,episode_n)]
        
      
    
      
    
    
    all_links=[]
    
    all_l=[]
    
    for search_url_1 in search_url:
      
        
        if stop_all==1:
            break
        
        x=get_html(f'https://www.1337xx.to/search/{search_url_1}/1',headers=base_header,timeout=10,verify=False).content()
        log.warning(f'https://www.1337xx.to/search/{search_url_1}/1')
        regex='<tr bgcolor(.+?)</tr>'
        m_pre=re.compile(regex,re.DOTALL).findall(x)
        log.warning(m_pre)
        for item in m_pre:
            if stop_all==1:
                break
            regex='flaticon.+?href="(.+?)".+?id-text="(.+?)".+?coll-4 size mob-uploader">(.+?)<'
            
            
            m=re.compile(regex,re.DOTALL).findall(item)
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                i=0
                for lk,nm,size in m:
                    
                    futures.append(executor.submit(trd_data, lk,nm,size))
                    i+=1
                wait(futures)
        
        global_var=all_links
               
                
                         
    
    return global_var
        
    