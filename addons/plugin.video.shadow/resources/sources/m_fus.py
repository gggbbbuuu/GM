# -*- coding: utf-8 -*-
import re
import time,xbmc

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
    
    # ====== PERFORMANCE: Cache max_size before loop ======
    max_size = int(Addon.getSetting("size_limit"))
    
    imdb_id=cache.get(get_imdb, 999,tv_movie,id,table='pages')
    manifest = '/D-MIbpwuk3VD5_CHRJs83prr7cYNsEeES33_q5H_20vS5qUu7BRIAQxRAPvx5MqmsWieumYH7LMiomgKfTEZpueYYgxvL81e3uYVYKH7dSE2jqFPmU4NEdlZ4-Olu5WlULZ8460eBJ0GMfOkS0A9ohEnRZOOZXzNr3JOoZ1Hgh6OTHiCLG2KCgIUk1ciP1s43vHSwhm1k4rVg3bDrRIuyGieBE_-BJMTKqKNTuxupujI3jB3FV6oifJDO6VMtGWeovc8aRCYeWvdVb_osJOPzW3H7DXnyp78-kq0xv7vAxsELsT5MclPS1ZGiATZ5lD0l58RvvZfNzXdo7ZZkmTiTqcdnVYzWeGUwOqn6bCHXo7gzrpzS96WC17UYWDKI13B50i4wOFtIIl3GZ8EXWzM3Bq70cKGZNa9ntPgrPp4dvLH-Vcgdt9BjXGP-WWhhnRQcff7-sytlVFMYA_8BzrQhI4K2TOa9HtU9-kgV0yxszNY8DTqOt9ACJqhN83gOzWWAivY4C0V8pwCjKVPhVwjMZNqRjCQKgZv8ex-6Q2C18C20canoCDvvde1NOC1QAlsj0aY_Q99BDZC4P-p3OrJ_m6GV_Tmaj66ojWoZCive4njyOsG_wLsomCnc3z_ki8FLnYqcmasILPXSW9ncNzgQlIi30Y_JZo8rU5vukiWTzo0gQ43id7tZnB7gIMQzgZdX4j7T7YIWBRcPGwEHP53lbI4rBFgaesSRYFuomdSXrhzQ1R-m3mgL8VS4mZDlfFFdtU_1IM5iolxUyqpIfvWJupWv5O_NfNfdTRTLTUhRJ51JEK6gM79kTwxWywkIZurXnm8Nvq-oywcVgaUQmTk641Ay45fCrkutPRFDEJNWATGtnt_KC6P40joilP1Fn3YIfn8WYluzgBut0jPTI8j4R5FxzwbSQn91fWuGziODAq98IB_Zj0Hs48-b3c5nVRlbFHMOa0b-JSzok4rqHHm-rq9LHLu4Rgq71udlGSwwdUu8cdye8gaQ99lOsr7BPKib01m1qpXKBUV1qKwLGRhhYwDs_MhcwO6wgP-U-HPMdsxBXyr1z90vZyjTRB2-ld3wSD_7U50nK7PbdhKAryODYFRSERV-n90PNkYuZ4gxuJGgnN5aHfTkFx_2hlyMwa2n81pYfN602ZKyuvRr8vcaQlwqsnGgjpFtj6KjCZhPRZjid2l9iAJn49IFWI3dpsdWuQYR--AuIXISR3uxlhK_nS-v7B2P3nX8bEsYxjhU2kHtRiM7eC8tHcnxDSFJ0SV84wyitBDuzxZfMYKCPhoNwnCUOdMPprANs5_jUVJYsmJGCF7mX4-KXIqFDYtHOCtMSxxyuvDQMXA6AwaNxvBkIUW7S1OlgXFtBtEC_m7RZs1BiqNd6GEq-dsgcZF4Vexz_5tej_em_jUR4sqIWrCJJ5557xUcfN1omwGEggNLAndNMdblS8KqKOcxjRC9LxxepxA1BZF6c7-_ZlsuhbU3T5gvXIP_ASDeEz47nbt_zHwz3QSiLRtuagwFM8ZfR5ivcdO6CBPf3TsU-i6wUTfoXdXPUEOqG2lvzGiZ5aOWRLmI1-_Pd6ZUJgzXhssiW94vras8e_kpAP2KSbsY6n_Axc9CreePrOBdiprDJgHwLlCVedcRpJGNaCSh0zZ-qxr3KZhEWHGcCqufb-GCMAkMoLMDHmpjR1GwJsxN7xALEKtWAn3csEC4kedL662R9_Npe'
    
    added_season=''
    if tv_movie=='tv':
        tv_movie='series'
        added_season=':%s:%s'%(season,episode)
       
    url=f'https://mediafusion.elfhosted.com{manifest}/stream/{tv_movie}/{imdb_id}{added_season}.json'
    
   
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
    if not isinstance(x, dict):
        return global_var
    streams = x.get('streams')
    if streams is None:
        log.warning('MediaFusion unexpected payload: %s' % str(x)[:300])
        return global_var
    
   
    for results in streams:

            if stop_all==1:
                break
            
            # Try to get filename from behaviorHints first
            if 'behaviorHints' in results and 'filename' in results['behaviorHints']:
                nam = results['behaviorHints']['filename']
                
            else:
                # Construct from description
                file_title = results['description'].split('\n')
                nam = clean_name(file_title[0], 1).replace('📂 ','')
                
            
            # Extract size info
            file_title = results['description'].split('\n')
            _INFO = re.compile(r'📦.*')
            file_info_list = [x for x in file_title if _INFO.match(x)]
            if not file_info_list:
                continue
            file_info = file_info_list[0]
            size=file_info.split('📦')[1].split(' 👤')[0].strip()
            
            try:
                 o_size=size
                 
                 size=float(o_size.replace('GB','').replace('MB','').replace(",",'').strip())
                 if 'MB' in o_size:
                   size=size/1000
            except Exception as e:
                
                size=0
            
            # Try to extract hash - check multiple possible locations
            hash = None
            
            # First, check if there's an infoHash field directly in the result
            if 'infoHash' in results:
                hash = results['infoHash']
                
            # For movies with /torbox/ URLs
            elif '/torbox/' in results['url']:
                hash = results['url'].split('/torbox/')[-1].split('/')[0]
                
            # Try to get from URL last segment (for simple movie URLs)
            else:
                url_parts = results['url'].split('/')
                # Skip if last part looks like a filename - need to look elsewhere
                if not url_parts[-1].endswith(('.mkv', '.mp4', '.avi')):
                    hash = url_parts[-1]
                    
            
            # If no hash from URL, try extracting from description (🔑 marker)
            if not hash:
                for line in results['description'].split('\n'):
                    if '🔑' in line:
                        hash = line.split('🔑')[1].strip()
                        
                        break
            
            if not hash:
                log.warning('No hash found, skipping this result')
                continue
                
            links=hash
            lk='magnet:?xt=urn:btih:%s&dn=%s'%(links,que(original_title))
            
            # Check resolution in filename (case-insensitive)
            nam_lower = nam.lower()
            if '4k' in nam_lower or '2160p' in nam_lower or '2160' in nam_lower:
                  res='2160'
            elif '1080p' in nam_lower or '1080' in nam_lower:
                  res='1080'
            elif '720p' in nam_lower or '720' in nam_lower:
                  res='720'
            elif '480p' in nam_lower or '480' in nam_lower:
                  res='480'
            elif '360p' in nam_lower or '360' in nam_lower:
                  res='360'
            else:
                  res='HD'
            max_size=int(Addon.getSetting("size_limit"))
            
            
            if (size)<max_size:
               
                all_links.append((nam,lk,str(size),res))

                global_var=all_links
    return global_var