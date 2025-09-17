# -*- coding: utf-8 -*-
import re
import time

global global_var,stop_all#global
global_var=[]
stop_all=0
from  resources.modules.client import get_html
 
from resources.modules.general import clean_name,check_link,server_data,replaceHTMLCodes,domain_s,similar,all_colors,base_header
from  resources.modules import cache
from resources.modules import log
try:
    from resources.modules.general import Addon
except:
  import Addon
type=['movie','tv','torrent']

import urllib,logging,base64,json
def _get_token_and_cookies( url):
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,he;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://bitlordsearch.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://bitlordsearch.com/get_list',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        # 'cookie': '_ym_uid=175800472925726897; _ym_d=1758004729; _ym_isad=2; _ym_visorc=w',
    }

    json_data = {
        'username': 'bls_super_admin',
        'password': '2jLPgYIKsgl5TZ_I',
    }

    response = get_html('https://bitlordsearch.com/api/token/', headers=headers, json=json_data,post=True).json()
    
    return (response['access'],response['refresh'])
def _get_token_and_cookies_old( url):
    headers = {
        'authority': 'bitlordsearch.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'accept': '*/*',
        'dnt': '1',
        
        'x-requested-with': 'XMLHttpRequest',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.193 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://bitlordsearch.com',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
       
        
        
    }
    token=''
    x,cook = get_html(url,get_cookies=True,headers=headers).content()
    log.warning(f"data:{x}")
    regex='token: (.+?)\n'
    m=re.compile(regex).findall(x)
    
    regex="var %s = '(.+?)'"%m[0]
    m2=re.compile(regex).findall(x)
    token=m2[0]
    regex=">%s \+= '(.+?)'"%m[0]
    m3=re.compile(regex).findall(x)
    for itt in m3:
        token+=itt
    cookies = ''
    for cookie in cook:
        cookies += '%s=%s;' % (cookie, cook[cookie])
    return (token,cookies)
    
def get_links(tv_movie,original_title,season_n,episode_n,season,episode,show_original_year,id):
    global global_var,stop_all
    all_links=[]
    url='https://bitlordsearch.com'
    
    token,cookies=_get_token_and_cookies( url)
    
    #headers = {
    #    'x-request-token': token,
    #    'cookie': cookies
    #}
    
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,he;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'authorization': f'Bearer {token}',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'dnt': '1',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://bitlordsearch.com/get_list',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        
    }

    if tv_movie=='tv':
        if Addon.getSetting('debrid_select')=='0' :
            query=[clean_name(original_title,1)+'+s%s'%(season_n),clean_name(original_title,1)+'+s%se%s'%(season_n,episode_n),clean_name(original_title,1)+'+season+' +season]
            query=[clean_name(original_title,1)+'+season+' +season]
        else:
            query=[clean_name(original_title,1)+'+s%se%s'%(season_n,episode_n)]
            
    else:
        query=[clean_name(original_title,1)+' '+show_original_year]
    for qrr in query:
      
        
        data = {
            'query': qrr,
            'offset': 0,
            'limit': 99,
            'filters[field]': 'seeds',
            'filters[sort]': 'desc',
            'filters[time]': 4,
            'filters[category]': 3 if tv_movie=='movie' else 4,
            'filters[adult]': False,
            'filters[risky]': False
        }
        params = {
            'limit': '99',
            'offset': '0',
            'is_verified': 'true',
            'adult': 'false',
            'category': 'Movies & Video' if tv_movie=='movie' else 'Series',
            'title': qrr,
            'sort_seeds': 'down',
        }
        response = get_html("https://bitlordsearch.com/api/list/",  params=params, headers=headers,timeout=10).json()
        
        for el in response:
                #size is broken in new api
            
                
                
               
               
                #max_size=int(Addon.getSetting("size_limit"))
                title=el['fulltext_index']
              
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

                if 1:
                              
                       all_links.append((el['fulltext_index'],el['magnet_link'],0,res))
                   
                       global_var=all_links
    return global_var
        
    