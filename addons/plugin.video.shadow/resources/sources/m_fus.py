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
def clean_name(release_title):
    try:
        release_title = re.sub(r'【.*?】', '', release_title)
        release_title = strip_non_ascii_and_unprintable(release_title).lstrip('+.-:/ ').replace(' ', '.')
        releasetitle_startswith = release_title.lower().startswith
        if releasetitle_startswith('rifftrax'): return release_title # removed by "undesirables" anyway so exit
        for i in unwanted_tags:
            if releasetitle_startswith(i):
                release_title = re.sub(r'^%s' % i.replace('+', '\+'), '', release_title, 1, re.I)
        release_title = release_title.lstrip('+.-:/ ')
        release_title = re.sub(r'^\[.*?]', '', release_title, 1, re.I)
        release_title = release_title.lstrip('.-[](){}:/')
        return release_title
    except Exception as  e:
        
        log.warning(e)
        return release_title
        

def get_links(tv_movie,original_title,season_n,episode_n,season,episode,show_original_year,id):
    global global_var,stop_all
    all_links=[]
    imdb_id=cache.get(get_imdb, 999,tv_movie,id,table='pages')
    manifest = '/eJwB8AEP_vTC0-41NtYccYs7wZ6l1qeUToHNnQsAey_kuyGCAppcyY1b_JgPiJL_zMEUp8S1FLMb55AUklkc4UG8frNbiX2UfYRzFX4uwFcJaaj3nTmJp4chEvKy2QRhVuo2CZ36tLh9p7EhN0GIA-vW-WFRrarkaklb6xn9mdL4GtBI8PkWsF1hYuX5mW492hZHV6CjIFkUiik4i8IYTkW3oGZnfl-0p7p4GExfDnvbCBONdHuj6M_N5cqwbQD1SiU5VZ6n_h2ABOpGRytAcjzj86RkTGFvcO-flBrkQURCMh3Bl01MDO--B0Bo9DKFBgtdEww13nlI2seJp3OoTUwOc2JAqyYM_IBMKkJCyROvXrfHG-mQ_5kAqHIawgHkQU3F9GgotHbX9g8FaCFWyNR0psNTfJfNAmdSqpXWKlfAvxdwLGIK-rWxKayDCFOD0oAMQYVCG7Km43PYGXRHktz4zeeSOY34q7shmHHV3_XIgb0X04Bf4DQuo25kbawU8ez6kuu_0niSK0gfZh3HgEl6SyM70aEme91EEgu4cyKp5ateGwgRMz9ZmGAmVLYP6uKwF_XXJS6xalaY-R9X6ukUjkAquj-zTTM-VCRa8bF0_m8QZoXlupIq1U4gVDvdRCFqsyVJPX_Q_PoK-TvNYF2eMZY2CMXo8vCt'
    
    added_season=''
    if tv_movie=='tv':
        tv_movie='series'
        added_season=':%s:%s'%(season,episode)
    url=f'https://mediafusion.elfhosted.com{manifest}/stream/{tv_movie}/{imdb_id}{added_season}.json'
    
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
            file_title = results['description'].split('\n')
            _INFO = re.compile(r'💾.*')
            file_info = [x for x in file_title if _INFO.match(x)][0]
            nam = clean_name(file_title[0]).replace('📂 ','')
            #nam=results['title'].split('\n💾')[0]
            size=results['description'].split('\n💾')[1].split(' 👤')[0]
            try:
                 o_size=size
                 
                 size=float(o_size.replace('GB','').replace('MB','').replace(",",'').strip())
                 if 'MB' in o_size:
                   size=size/1000
            except Exception as e:
                
                size=0
            if tv_movie=='series':
                hash = results['url'].split('info_hash=')[1]
                hash = hash.split('&season=')[0]
            else:
                hash = results['url'].split('info_hash=')[1]
            links=hash
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