# -*- coding: utf-8 -*-
import re
import time
from  resources.modules.client import get_html
global global_var,stop_all#global
global_var=[]
stop_all=0
from resources.modules import log
 
from resources.modules.general import clean_name,check_link,server_data,replaceHTMLCodes,domain_s,similar,cloudflare_request,all_colors,base_header
from  resources.modules import cache
try:
    from resources.modules.general import Addon
except:
  import Addon
type=['movie','tv','torrent']

import urllib,logging,base64,json

def get_links(tv_movie,original_title,season_n,episode_n,season,episode,show_original_year,id):
    global global_var,stop_all
    if tv_movie=='movie':
      search_url=[clean_name(original_title,1).replace(' ','%20')+'%20']
      s_type='Movies'
      type='003000000'
      type2='201'
    else:
      if Addon.getSetting('debrid_select')=='0' :
        search_url=[clean_name(original_title,1).replace(' ','%20')+'%20s'+season_n+'e'+episode_n,clean_name(original_title,1).replace(' ','%20')+'%20s'+season_n,clean_name(original_title,1).replace(' ','%20')+'%20season%20'+season]
      else:
        search_url=[clean_name(original_title,1).replace(' ','%20')+'%20s'+season_n+'e'+episode_n]
      s_type='TV'
      type='002000000'
      type2='205'
    
    cookies = {
        'filter': '%7B%22search%22%3A%22fast%22%2C%22hideXXX%22%3Atrue%2C%22unsafe%22%3Afalse%7D',
    }
    all_links=[]
    
    all_l=[]

    for itt in search_url:
      for page in range(0,7):
        if stop_all==1:
            break
        url=f'https://knaben.eu/search/{itt}/{type}/{page}/seeders'
        log.warning(url)
        x=get_html(url,headers=base_header,timeout=10,cookies=cookies).content()
        
   
        regex='<tr (.+?)</tr>'
        
        m_pre=re.compile(regex,re.DOTALL).findall(x)
      
        if len(m_pre)==0:
            break
        for items in m_pre:
            
            regx='a title="(.+?)".+?href="(.+?)".+?Bytes">(.+?)<'
            m=re.compile(regx,re.DOTALL).findall(items)
        
            for title,link,size in m:
                             if 'magnet' not in link:
                                 continue
                             
                             if stop_all==1:
                                break
                             try:
                                 o_size=size
                                 
                                 size=float(o_size.replace('GB','').replace('MB','').replace(",",'').strip())
                                 if 'MB' in o_size:
                                   size=size/1000
                             except Exception as e:
                                
                                size=0
                             
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
                            
                             o_link=link
                             if 'https://knaben.eu/live' in link:
                                continue
                             try:
                                 o_size=size
                                 
                                 size=float(o_size.replace('GB','').replace('MB','').replace(",",'').strip())
                                 if 'MB' in o_size:
                                   size=size/1000
                             except Exception as e:
                                
                                size=0
                             max_size=int(Addon.getSetting("size_limit"))
                            
                             if size<max_size:
                             
                               all_links.append((title,link,str(size),res))
                           
                               global_var=all_links
                         
    
                         
    return global_var
        
    