#!/usr/bin/env python3
# countasync.py


#(f'https://api.themoviedb.org/3/movie/603?api_key={tmdb_key}&language=en-US',verify=False).json()


import time,sys,random,os
from concurrent.futures import wait
from  resources.modules.public import addNolink,addDir3,addLink,lang,user_dataDir
import json
from  resources.modules.client import get_html
from resources.modules import cache
import concurrent.futures
import xbmcplugin,xbmcgui
from urllib.parse import urlencode
from resources.modules import log
from  resources.modules.general import addon_id
cacheFile=os.path.join(user_dataDir,'database.db')
import xbmcaddon,xbmc
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database
Addon = xbmcaddon.Addon()
window=xbmcgui.Window(10000)
backup_resolutions, writer_credits = {'poster': 'w780', 'fanart': 'w1280', 'still': 'original', 'profile': 'h632'}, ('Author', 'Writer', 'Screenplay', 'Characters')
tmdb_key=Addon.getSetting("tmdb_api")
KODI_VERSION = int(xbmc.getInfoLabel("System.BuildVersion").split('.', 1)[0])
addon_id="plugin://"+addon_id

def meta_get(video_data,item):
    if item=='year' or item=='rating' or item=='votes' or item=='duration' or item=='playcount':
        return video_data.get(item,'0')
    if item=='country' or item=='cast':
        return video_data.get(item,[])
    return video_data.get(item,' ')
def get_html_g():
    try:
        url_g=f'https://api.themoviedb.org/3/genre/tv/list?api_key={tmdb_key}&language='+lang
        html_g_tv=get_html(url_g).json()
         
   
        url_g=f'https://api.themoviedb.org/3/genre/movie/list?api_key={tmdb_key}&language='+lang
        html_g_movie=get_html(url_g).json()
    except Exception as e:
        log.warning('Err in HTML_G:'+str(e))
    return html_g_tv,html_g_movie
html_g_tv,html_g_movie=cache.get(get_html_g,72, table='posters')

class tmdb:
    def __init__(self,action,url,heb_name='',original_title='',id=''):
        Addon = xbmcaddon.Addon()
        self.all_results={}
        self.all_tv_w={}
        self.all_w_tv_data={}
        self.all_tv_w_ep={}
        self.all_movie_w=[]
        self.season_watched={}
        self.season_watched_marked={}
        if Addon.getSetting("trakt_access_token")!='' and Addon.getSetting("trakt_info")=='true':
            try:
                self.get_trakt_data(url)
            except:
                pass
        self.all_lists=[]
        self.data_type=''
        if '/movie' in url:
            self.tv_movie='movie'
        else:
            self.tv_movie='tv'
        self.all_ids=[]
        self.main_data={}
        self.url=url
        self.all_d={}
        self.simple_data=False
        if action=='get_movies':
            self.get_movies()
        elif action=='get_seasons':
            self.get_seasons()
        elif action=='get_episodes':
            self.heb_name,self.original_title,self.id=heb_name,original_title,id
            
            self.get_episodes()
        
        
            
    def get_trakt_data(self,url):
        from  resources.modules.general import call_trakt
        self.all_movie_w=[]
        if '/movie' in url:
               try:
                   i = (call_trakt('/users/me/watched/movies'))
                   
                   for ids in i:
                      self.all_movie_w.append(str(ids['movie']['ids']['tmdb']))
               except Exception as e:
                log.warning(e)
                pass
      
        self.all_tv_w={}
        self.all_w_tv_data={}
        self.all_tv_w_ep={}
        if '/tv' in url:
          
           i = (call_trakt('/users/me/watched/shows?extended=full'))
           
           for ids in i:
             aired_episodes=ids['show']['aired_episodes']
             self.all_tv_w[str(ids['show']['ids']['tmdb'])]='no'
             count_episodes=0
             self.all_tv_w_ep[str(ids['show']['ids']['tmdb'])]=[]
             for seasons in ids['seasons']:
              
              for ep in seasons['episodes']:
               
                count_episodes+=1
             
                self.all_tv_w_ep[str(ids['show']['ids']['tmdb'])].append(str(seasons['number'])+'x'+str(ep['number']))
             if count_episodes>=int(aired_episodes):
                    self.all_w_tv_data[str(ids['show']['ids']['tmdb'])]='yes'
          
    def get_movies(self):
        self.all_results,self.all_ids,self.main_data=self.local_cache(self.build_data,24,self.url)
        
        self.add_dir()
    def set_PRAGMAS(self, dbcon):
        
        
        dbcur = dbcon.cursor()
        dbcur.execute('''PRAGMA synchronous = OFF''')
        dbcur.execute('''PRAGMA journal_mode = OFF''')
        
        return dbcur
    def get_property(self,prop):
        return window.getProperty(prop)
    def set_property(self,prop,value):
        return window.setProperty(prop,value)
        
    def local_cache(self,function,timeout,url):
        
        cachedata = self.get_property(url)
        if cachedata:
            self.all_results,self.all_ids,self.main_data,saved_time=eval(cachedata)
            self.all_results=json.loads(self.all_results)
            self.all_ids=json.loads(self.all_ids)
            self.main_data=json.loads(self.main_data)
            t1 = int(saved_time)
            t2 = int(time.time())

            update = (abs(t2 - t1) / 3600) >= int(timeout)
            
            if update == True:
               
                t=time.time()
                self.all_results,self.all_ids,self.main_data=function(url)
                c= (json.dumps(self.all_results), json.dumps(self.all_ids), json.dumps(self.main_data),t)
                c = self.set_property(url,repr(c))
                
                
                
  
        if not cachedata or self.all_ids==[]:
            
           
            dbcon = database.connect(cacheFile)
            dbcur=self.set_PRAGMAS(dbcon)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS %s ( ""url TEXT, ""all_results TEXT, ""all_ids TEXT, ""main_data TEXT,""added TEXT, ""free TEXT);" % 'local_cache')
            
            dbcur.execute("SELECT * FROM local_cache WHERE url = '%s'" % (url))
            match = dbcur.fetchone()
            
            t = int(time.time())
            if match!=None:
                self.all_results,self.all_ids,self.main_data=json.loads(match[1]),json.loads(match[2]),json.loads(match[3])
                
                t1 = int(match[4])
                t2 = int(time.time())
                update = (abs(t2 - t1) / 3600) >= int(timeout)
                if update == True:
                    self.all_results,self.all_ids,self.main_data=function(url)
                    cachedata = (json.dumps(self.all_results), json.dumps(self.all_ids), json.dumps(self.main_data),t)
                    cachedata = self.set_property(url,repr(cachedata))
                    
                    
                    dbcur.execute("INSERT INTO local_cache Values (?, ?, ?, ?, ?, '')" , (url, json.dumps(self.all_results), json.dumps(self.all_ids), json.dumps(self.main_data),t))
                    dbcon.commit()
                
                return self.all_results,self.all_ids,self.main_data
                        
            else:
                
                self.all_results,self.all_ids,self.main_data=function(url)
                
                cachedata = (json.dumps(self.all_results), json.dumps(self.all_ids), json.dumps(self.main_data),t)
                cachedata = self.set_property(url,repr(cachedata))
                
                
                dbcur.execute("INSERT INTO local_cache Values (?, ?, ?, ?, ?, '')" , (url, json.dumps(self.all_results), json.dumps(self.all_ids), json.dumps(self.main_data),t))
                dbcon.commit()
            dbcur.close()
            dbcon.close()
        return self.all_results,self.all_ids,self.main_data
    def get_more_meta(self,id,iconimage,fanart):
      try:
        all_clear_art=[]
        all_n_fan=[]
        all_banner=[]
        r_banner=''
        r_back=''
        r_art=''
        r_logo=''
        art={'fanart':fanart,'iconimage':iconimage,'clearlogo':r_logo,'clearart':r_art,'icon': iconimage, 'thumb': fanart, 'poster': iconimage,'tvshow.poster': iconimage, 'season.poster': iconimage,'banner': r_banner, 'landscape': r_back, 'discart': iconimage}
    
        user = 'cf0ebcc2f7b824bd04cf3a318f15c17d'

        headers = {'api-key': 'a7ad21743fd710fccb738232f2fbdcfc'}

        headers.update({'client-key': user})
       
        m_type='movies'
        f_id=id
        
        full_art=get_html('http://webservice.fanart.tv/v3/%s/%s'%(m_type,f_id),headers=headers).json()

        logo=full_art.get('hdmovielogo','')
        if len(logo)>0:
            all_logo=[]
            for itt in logo:
              if itt['lang']=='en':
                all_logo.append(itt['url'])
            random.shuffle(all_logo)
            r_logo=all_logo[0]
        if 'hdmovieclearart' in full_art:
            for itt in full_art['hdmovieclearart']:
               if itt['lang']=='en':
                all_clear_art.append(itt['url'])
            
        if len(all_clear_art)>0:
            random.shuffle(all_clear_art)
            r_art=all_clear_art[0]
        if 'moviebackground' in full_art:
            for itt in full_art['moviebackground']:
               if itt['lang']=='en':
                all_n_fan.append(itt['url'])
        
        if len(all_n_fan)>0:
            random.shuffle(all_n_fan)
            r_back=all_n_fan[0]
        if 'moviebanner' in full_art:
            for itt in full_art['moviebanner']:
               if itt['lang']=='en':
                all_banner.append(itt['url'])
        
        if len(all_n_fan)>0:
            random.shuffle(all_n_fan)
            r_banner=all_clear_art[0]
        art={'fanart':fanart,'iconimage':iconimage,'clearlogo':r_logo,'clearart':r_art,'icon': iconimage, 'thumb': fanart, 'poster': iconimage,'tvshow.poster': iconimage, 'season.poster': iconimage,'banner': r_banner, 'landscape': r_back, 'discart': iconimage}

        return art
      except Exception as e:
            import linecache,sys
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
           
            log.warning('ERROR IN GET Art:'+str(lineno))
            log.warning('inline:'+line)
            log.warning(e)
            return art
    def get_response(self,req_url, timeout=10):
            return get_html(req_url, timeout=timeout,verify=False).json()
    def collect_meta(self,req_url, timeout=10):
        response = cache.get(self.get_response,24,req_url, table='posters')
       
        iconimage='https://image.tmdb.org/t/p/original/'+(response.get('poster_path','') or "")
        fanart='https://image.tmdb.org/t/p/original/'+(response.get('backdrop_path','') or "")
        self.all_results[response['id']]={}
        self.all_results[response['id']]['result']=response
        if self.tv_movie=='movie':
            self.all_results[response['id']]['art']=self.get_more_meta(response['id'],iconimage,fanart)
        else:
            self.all_results[response['id']]['art']={'fanart':fanart,'iconimage':iconimage,'icon': iconimage, 'thumb': fanart, 'poster': iconimage}
        return self.all_results
    def build_data(self,url):
        log.warning(url)
        self.get_response(self.url)
        data=cache.get(self.get_response,24,self.url, table='posters') 
        
        all_urls = [f"https://api.themoviedb.org/3/%s/%s?api_key={tmdb_key}&language=en&append_to_response=external_ids,videos,credits,release_dates,alternative_titles,translations"%(self.tv_movie,i['id']) for i in data['results']]
        
        self.all_ids=[i['id'] for i in data['results']]
        self.main_data={}
        x=0
        for i in data['results']:
            id=str(i.get('id'))
            self.main_data[id]={}
            self.main_data[id]['results']=i
            self.main_data[id]['main']=data
            self.main_data[id]['order']=x
            x+=1
        if Addon.getSetting("extra_data")=='true':
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for url in all_urls:
                    futures.append(executor.submit(self.collect_meta, req_url=url))
                wait(futures)
        return self.all_results,self.all_ids,self.main_data
        
    def get_main_data(self,id):
       try:
        
        video_data={}
        remove_record=False
        html=self.main_data[id]['main']
        data=self.main_data[id]['results']
        max_page=html['total_pages']
        all_res=html['total_results']
        
        rating=data.get('vote_average',0)
        
        plot=data.get('overview','')
           
        if Addon.getSetting("adults")=='true':
             
            addults=data.get('adult',False)
            
       
            if 'erotic ' in plot.lower() or 'sex' in plot.lower() or addults==True :
                remove_record=True
            
        if 'title' not in data:
           tv_movie='tv'
           new_name=data['name']
           html_g=html_g_tv
        else:
           tv_movie='movie'
           new_name=data['title']
           html_g=html_g_movie
          
        
         
        if 'original_title' in data:
           original_name=data['original_title']
        else:
           original_name=data['original_name']
        iconimage='https://image.tmdb.org/t/p/original/'+data.get('poster_path','')
        fanart='https://image.tmdb.org/t/p/original/'+html.get('backdrop_path','')
        genres_list= dict([(i['id'], i['name']) for i in html_g['genres'] \
                if i['name'] is not None])
        try:genere = u' / '.join([genres_list[x] for x in data['genre_ids']])
        except:genere=''
         
        trailer = "%s?mode=25&id=%s&url=%s" % (addon_id,id,tv_movie)
     
        if 'first_air_date' in data:
           year=str(data['first_air_date'].split("-")[0])
        elif 'release_date' in data:
            year=str(data['release_date'].split("-")[0])
        else:
            year='0'
  
        video_data['title']=new_name
        video_data['mediatype']='movie'
        video_data['TVshowtitle']=''
        
        video_data['season']=' '
        video_data['episode']=' '
        video_data['OriginalTitle']=original_name
        
        video_data['year']=year
        
        video_data['genre']=genere
        video_data['rating']=str(rating)
        video_data['trailer']=trailer

        video_data['plot']=plot
     
        #video_data['iconimage']=iconimage
        #video_data['fanart']=fanart
        
        return video_data
       except Exception as e:
            import linecache,sys
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
           
            log.warning('ERROR IN Main Data:'+str(lineno))
            log.warning('inline:'+line)
            log.warning(e)
            return video_data
    def get_ep_watched(self,season):
        try:
            from sqlite3 import dbapi2 as database
        except:
            from pysqlite2 import dbapi2 as database
        cacheFile=os.path.join(user_dataDir,'database.db')
        dbcon = database.connect(cacheFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS %s ( ""name TEXT, ""tmdb TEXT, ""season TEXT, ""episode TEXT,""playtime TEXT,""total TEXT, ""free TEXT);" % 'playback')
        dbcon.commit()
        
        dbcur.execute("SELECT * FROM playback where tmdb='%s' and season='%s' "%(self.id,str(season)))
        match = dbcur.fetchall()
       
        all_w={}

        for n,t,s,e,p,t,f in match:
            ee=str(e)
            all_w[ee]={}
            all_w[ee]['resume']=str(p)
            all_w[ee]['totaltime']=str(t)
        return all_w
    def get_watched(self):
        
        cacheFile=os.path.join(user_dataDir,'database.db')
        dbcon = database.connect(cacheFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS %s ( ""name TEXT, ""tmdb TEXT, ""season TEXT, ""episode TEXT,""playtime TEXT,""total TEXT, ""free TEXT);" % 'playback')

       
        dbcon.commit()
   
        dbcur.execute("SELECT * FROM playback")
        match = dbcur.fetchall()
        dbcur.close()
        dbcon.close()
        all_w={}
          
        for n,tm,s,e,p,t,f in match:
                ee=str(tm)
                all_w[ee]={}
                if self.tv_movie=='movie':
                    all_w[ee]['resume']=str(p)
                    all_w[ee]['totaltime']=str(t)
                else:
                    all_w[ee]['resume']=0
                    all_w[ee]['totaltime']=100
        return all_w
    def add_items(self,data_pre,tv_movie,order):
       try:
        if 'result' in data_pre:
            data_get=data_pre['result'].get 
        else:
            data_get=data_pre['results'].get 
        id=str(data_get('id'))
       
        
        
       
        
        
        
        video_data=self.get_main_data(id)
        #log.warning(video_data['title']+', '+id+','+added_pre)
        
        heb_name=video_data['title']
        cast=[]
        writer=''
        director=''
        mpaa=[]
        total_aired_eps=''
        total_seasons=''
        #season_data, total_seasons, total_aired_eps = data_get('seasons'), data_get('number_of_seasons'), data_get('number_of_episodes')
        log.warning("extra_data2")
        log.warning(Addon.getSetting("extra_data"))
        if Addon.getSetting("extra_data")=='true':
            log.warning("1")
            
            
            tmdb_id, imdb_id = data_get('id', ''), data_get('imdb_id', '')
            votes = data_get('vote_count', '')
            if tv_movie=='movie':
                
                try: duration = int(data_get('runtime', '90') * 60)
                except: duration = 90 * 60
                
            else:
                try: duration = min(data_get('episode_run_time'))*60
                except: duration = 30*60
                season_data, total_seasons, total_aired_eps = data_get('seasons'), data_get('number_of_seasons'), data_get('number_of_episodes')
            credits = data_get('credits')
            if credits:
                all_cast = credits.get('cast', None)
                
                if all_cast:
                    try: cast = [{'name': i['name'], 'role': i['character'], 'thumbnail': 'https://image.tmdb.org/t/p/%s%s' % (backup_resolutions['profile'], i['profile_path'])if i['profile_path'] else ''}\
                                for i in all_cast]
                    except Exception as e:
                        log.warning(e)
                
                crew = credits.get('crew', None)
                if crew:
                    try: writer = ', '.join([i['name'] for i in crew if i['job'] in writer_credits])
                    except: pass
                    try: director = [i['name'] for i in crew if i['job'] == 'Director'][0]
                    except: pass
            release_dates = data_get('release_dates')
            if release_dates:
                try: mpaa = [x['certification'] for i in release_dates['results'] for x in i['release_dates'] \
                            if i['iso_3166_1'] == 'US' and x['certification'] != '' and x['note'] == ''][0]
                except: mpaa=[]
            if tv_movie=='movie':
                premiered =  data_get('release_date', '')
            else:
                premiered =  data_get('first_air_date', '')
            companies = data_get('production_companies')
            studio=[]
            if tv_movie=='tv':
                networks = data_get('networks', None)
                if networks:
                    if len(networks) == 1: studio = [i['name'] for i in networks][0]
                    else:
                        try: studio = [i['name'] for i in networks if i['logo_path'] not in empty_value_check][0] or [i['name'] for i in networks][0]
                        except: pass
            else:
                if companies:
                    if len(companies) == 1: studio = [i['name'] for i in companies][0]
                    else:
                        try: studio = [i['name'] for i in companies if i['logo_path'] not in empty_value_check][0] or [i['name'] for i in companies][0]
                        except: pass
            production_countries = data_get('production_countries', None)
            country_codes=[]
            country=[]
            if production_countries:
                country = [i['name'] for i in production_countries]
                country_codes = [i['iso_3166_1'] for i in production_countries]
            iconimage='https://image.tmdb.org/t/p/original/'+(data_get('poster_path','') or "")
            fanart='https://image.tmdb.org/t/p/original/'+(data_get('backdrop_path','') or "")
            tagline=data_get('tagline', '')
            
            
            #video_data['cast']=cast
            video_data['writer']=writer
            video_data['director']=director
            video_data['duration']=duration
            #video_data['imdb']=imdb_id
            video_data['votes']=votes
            video_data['mpaa']=mpaa
            #video_data['country_codes']=country_codes
            video_data['country']=country
            video_data['studio']=studio
            video_data['premiered']=premiered
        else:
            iconimage='https://image.tmdb.org/t/p/original/'+(data_get('poster_path','') or "")
            fanart='https://image.tmdb.org/t/p/original/'+(data_get('backdrop_path','') or "")
            imdb_id=id
            data_pre['art']={'fanart':fanart,'iconimage':iconimage,'clearlogo':'','clearart':'','icon': iconimage, 'thumb': fanart, 'poster': iconimage,'tvshow.poster': iconimage, 'season.poster': iconimage,'banner': '', 'landscape': ''}
                
               
            
        video_data['mediatype']='movie'
        video_data['TVshowtitle']=''
      
        video_data['season']=0
        video_data['episode']=0
        link=self.url.split('page=')[0]
        page_no=self.url.split('page=')[1]

        params={}
        params['iconimage']=iconimage
        params['fanart']=fanart
        params['description']=video_data['plot']
        params['url']=link+'page='+str(int(page_no)+1)
        params['name']=video_data['title']
        params['season']=' '
        params['episode']=' '
        params['heb_name']=heb_name
        params['original_title']=video_data['OriginalTitle']
        if self.tv_movie=='movie':
            params['mode']=15
            isfolder=False
        else:
            params['mode']=16
            isfolder=True
        params['id']=id
 
        params['tmdbid']=id
        params['eng_name']=video_data['title']
        params['show_original_year']=video_data['year']
        params['data']=video_data['year']
        url_params = f'{addon_id}/?' + urlencode(params) 
        self.all_d[id]={}
        self.all_d[id]['url_params']=url_params
        self.all_d[id]['video_data']=video_data
        self.all_d[id]['cast']=cast
        self.all_d[id]['data_pre']=data_pre
        self.all_d[id]['total_aired_eps']=total_aired_eps
        self.all_d[id]['total_seasons']=total_seasons
        
        self.all_d[id]['imdb_id']=imdb_id
        
        self.all_d[id]['order']=order
        #self.all_lists.append((url_params, listitem, isfolder,order))
       except Exception as e:
            import linecache,sys
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
           
            log.warning('ERROR IN GET TMDB:'+str(lineno))
            log.warning('inline:'+line)
            log.warning(e)
    def thread_all_data(self,url):
        if Addon.getSetting("extra_data")=='true':
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                i=0
                for id in self.all_ids:
                    if id not in self.all_results:
                        id=str(id)
                   
                    
                    futures.append(executor.submit(self.add_items, data_pre=self.all_results[id],tv_movie=self.tv_movie,order=i))
                    i+=1
                wait(futures)
        else:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                i=0
                for id in self.all_ids:
                    if id not in self.all_results:
                        id=str(id)
                   
                    
                    futures.append(executor.submit(self.add_items, data_pre=self.main_data[id],tv_movie=self.tv_movie,order=i))
                    i+=1
                wait(futures)
        return self.all_d,{},{}
    def get_added_pre(self,id,all_w,episode=0):
        added_pre=''
        
        if self.tv_movie=='tv':
           ee=str(episode)
        else:
            ee=str(id)
        
        time_to_save_trk=int(Addon.getSetting("time_to_save"))
        all_w_trk=''
        if all_w_trk!='':
            if float(all_w_trk)>=time_to_save_trk:
                added_pre='  [COLOR yellow][I]'+'√'+'[/I][/COLOR] \n '
            elif float(all_w_trk)>1:# and float(all_w_trk)<time_to_save_trk:
                added_pre=' [COLOR yellow][I]'+str(int(float(all_w_trk)))+'%[/I][/COLOR] \n '
        elif ee in all_w:
              
              if '%' in str(all_w[ee]['resume']):
                all_w_time=all_w[ee]['resume'].replace('%','')
              else:
                all_w_time=int((float(all_w[ee]['resume'])*100)/float(all_w[ee]['totaltime']))
              
              if float(all_w_time)>=time_to_save_trk:
                    added_pre=' [COLOR yellow][I]'+'√'+'[/I][/COLOR] \n '
              elif float(all_w_time)>1:# and float(all_w_time)<time_to_save_trk:
               added_pre=' [COLOR yellow][I]'+str(all_w_time)+'%[/I][/COLOR] \n '
        return added_pre

    def get_menu_items(self,video_data,id):
        from resources.modules import public
        pre_mode=public.pre_mode
        menu_items=[]
        tv_show=tv_movie=self.tv_movie
        season='%20'
        episode='%20'
        
        if Addon.getSetting("cast")=='true':
                menu_items.append(('[I]%s[/I]'%Addon.getLocalizedString(32248), 'ActivateWindow(10025,"%s?mode=177&url=%s&id=%s&season=%s&episode=%s",return)'  % ( "%s/"%addon_id ,self.tv_movie,id,'%20','%20')))
        menu_items.append(('[I]%s[/I]'%Addon.getLocalizedString(32166), 'Action(Info)'))
        if Addon.getSetting("play_trailer")=='true':
            menu_items.append(('[I]%s[/I]'%Addon.getLocalizedString(32167), 'PlayMedia(%s)' % video_data['trailer']))
        if Addon.getSetting("settings_content")=='true':
            menu_items.append(('%s'%Addon.getLocalizedString(32168), 'RunPlugin(%s?mode=151&url=www)' % "%s/"%addon_id ))
        if Addon.getSetting("queue_item")=='true':
            menu_items.append(('%s'%Addon.getLocalizedString(32169), 'Action(Queue)' ))
        if Addon.getSetting("trakt_manager")=='true':
            menu_items.append((Addon.getLocalizedString(32170), 'RunPlugin(%s)' % ('%s?url=%s&mode=150&name=%s&data=%s')%("%s/"%addon_id,id,video_data['OriginalTitle'],tv_movie) ))
        if Addon.getSetting("trakt_watched")=='true':
            menu_items.append(('[I]%s[/I]'%Addon.getLocalizedString(32171), 'RunPlugin(%s)' % ('%s?url=www&original_title=add&mode=65&name=%s&id=%s&season=%s&episode=%s')%("%s/"%addon_id,tv_show,id,season,episode))) 
        if Addon.getSetting("trakt_unwatched")=='true':
            menu_items.append(('[I]%s[/I]'%Addon.getLocalizedString(32172), 'RunPlugin(%s)' % ('%s?url=www&original_title=remove&mode=65&name=%s&id=%s&season=%s&episode=%s')%("%s/"%addon_id,tv_show,id,season,episode))) 
        if Addon.getSetting("clear_Cache")=='true':
            menu_items.append(('[I]%s[/I]'%Addon.getLocalizedString(32176), 'RunPlugin(%s)' % ('%s?url=www&mode=35')%("%s/"%addon_id)))
        if Addon.getSetting("set_view_type")=='true' :
            menu_items.append(('[I]%s[/I]'%Addon.getLocalizedString(32177), 'RunPlugin(%s)' % ('%s?url=%s&mode=167')%(sys.argv[0],str(pre_mode))))
        
        return menu_items
    def add_dir(self,season=0):
        '''
        for id in self.all_ids:
            if id not in self.all_results:
                log.warning('False: '+str(id))
            else:
                log.warning('True: '+str(id))
        '''
        start=time.time()
        if self.simple_data==False:
            self.all_d,dummy1,dummy2=self.local_cache(self.thread_all_data,24,'data'+self.url)
        if self.data_type=='episodes':
            all_w=self.get_ep_watched(season)
        else:
            all_w=self.get_watched()
        
               
        
        for ids in self.all_d:
            
            url_params=self.all_d[ids]['url_params']
            video_data=self.all_d[ids]['video_data']
            cast=self.all_d[ids]['cast']
            data_pre=self.all_d[ids]['data_pre']
            total_aired_eps=self.all_d[ids]['total_aired_eps']
            total_seasons=self.all_d[ids]['total_seasons']
            order=self.all_d[ids]['order']
            #added_pre=self.all_d[ids]['added_pre']
            imdb_id=self.all_d[ids]['imdb_id']
            try:
                tmdb_id=str(self.all_d[ids]['tmdb'])
            except:
                tmdb_id=ids
            added_pre=self.get_added_pre(ids,all_w,episode=video_data.get('Episode',0))
            if added_pre!='':

                video_data['title']='[COLOR lightblue]'+video_data['title']+'[/COLOR]'
            video_data['title']=added_pre.replace('\n','')+video_data['title']
            
            menu_items=self.get_menu_items(video_data,ids)
            
            listitem=xbmcgui.ListItem(offscreen=True)
            
            listitem.setContentLookup(False)
            listitem.setLabel(added_pre+video_data['title'])
            
            
            #video_data['playcount']=0
            if ids in self.all_movie_w:
              video_data['playcount']=1
              video_data['overlay']=7
            
            if ids in self.all_w_tv_data:
                watched=self.all_w_tv_data[ids]
                if watched=='yes':
                    video_data['playcount']=1
                    video_data['overlay']=7
            
            if tmdb_id in self.all_tv_w_ep:
                
                if str(video_data.get('Season',0))+'x'+str(video_data.get('Episode',0)) in self.all_tv_w_ep[tmdb_id]:
                    watched='yes'
                    video_data['playcount']=1
                    video_data['overlay']=7
            
            if int(ids) in self.season_watched_marked:
                watched=self.season_watched_marked[int(ids)]
                if watched=='yes':
                    video_data['playcount']=1
                    video_data['overlay']=7
                
            listitem.setArt(data_pre.get('art',[]))
            if KODI_VERSION>19:
                info_tag = listitem.getVideoInfoTag()
                info_tag.setMediaType(meta_get(video_data,'mediatype'))
                info_tag.setTitle(meta_get(video_data,'title'))
                info_tag.setPlot(meta_get(video_data,'plot'))
                info_tag.setPlaycount(int(meta_get(video_data,'playcount')))
                
                try:
                    year_info=int(meta_get(video_data,'year'))
                    if (year_info>0):
                        info_tag.setYear(year_info)
                except:
                    pass
                info_tag.setRating(float(meta_get(video_data,'rating')))
                info_tag.setVotes(int(meta_get(video_data,'votes')))
                info_tag.setMpaa(str(meta_get(video_data,'mpaa')))
                info_tag.setDuration(int(meta_get(video_data,'duration')))
                info_tag.setCountries(meta_get(video_data,'country'))
                
                info_tag.setTrailer(meta_get(video_data,'trailer'))
                info_tag.setPremiered(meta_get(video_data,'premiered'))
                info_tag.setTagLine(meta_get(video_data,'tagline'))
                info_tag.setStudios((meta_get(video_data,'studio') or '',))
                info_tag.setUniqueIDs({'imdb': meta_get(video_data,'imdb'), 'tmdb':meta_get(video_data,'tmdb')})
                info_tag.setGenres(meta_get(video_data,'genre').split(', '))
                info_tag.setWriters(meta_get(video_data,'writer').split(', '))
                info_tag.setDirectors(meta_get(video_data,'director').split(', '))
                
                info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb':str(id)})
                all_cast_new=[]
                for item in cast:
                   all_cast_new.append(xbmc.Actor(name=item['name'], role=item['role'], thumbnail=item['thumbnail']))
                
                info_tag.setCast(all_cast_new)
            else:
                listitem.setCast(cast)
                listitem.setUniqueIDs({'imdb': imdb_id, 'tmdb': str(id)})
            
                listitem.setInfo('Video', infoLabels=video_data)
            listitem.addContextMenuItems(menu_items, replaceItems=False)
            isfolder=False
           
            if self.tv_movie=='tv':
                if self.data_type!='episodes':
                    isfolder=True
                #video_data['season_data']=season_data
                if total_aired_eps!='':
                    listitem.setProperty('totalepisodes', str(total_aired_eps))
                if total_seasons!='':
                    listitem.setProperty('totalseasons', str(total_seasons))
            if not(('√' in added_pre or video_data.get('playcount',0)==1) and Addon.getSetting("remove_watched")=='true'):
                self.all_lists.append((url_params, listitem, isfolder,order))  
        self.all_lists=sorted(self.all_lists, key=lambda x: x[3], reverse=False)
        
        if not self.simple_data:
            listitem=xbmcgui.ListItem(offscreen=True)
            listitem.setLabel('[COLOR aqua][I]Choose page[/I][/COLOR]')
            
            
            if KODI_VERSION>19:
                info_tag = listitem.getVideoInfoTag()
                
                info_tag.setTitle('[COLOR aqua][I]Choose page[/I][/COLOR]')
            else:
                listitem.setInfo('Video', infoLabels={'title':'[COLOR aqua][I]Choose page[/I][/COLOR]'})
            listitem.setArt({'fanart':'https://icon-library.com/images/next-page-icon-png/next-page-icon-png-13.jpg','icon':'https://www.shutterstock.com/image-vector/curled-corner-red-text-next-260nw-203435044.jpg','thumb':'https://www.shutterstock.com/image-vector/curled-corner-red-text-next-260nw-203435044.jpg'})
            
            params={}
            if 'page=' in self.url:
                link=self.url.split('page=')[0]
                page_no=self.url.split('page=')[1]
            else:
                link=self.url
                page_no='1'
            params['description']=''
            params['url']=link+'page='+str(int(page_no)+1)
            params['name']='[COLOR aqua][I]Choose page[/I][/COLOR]'
           
            params['heb_name']='[COLOR aqua][I]Choose page[/I][/COLOR]'
            
            params['mode']=206
           
            
            params['eng_name']='[COLOR aqua][I]Choose page[/I][/COLOR]'
         

            url_params = f'{addon_id}/?' + urlencode(params) 
            
            self.all_lists.append((url_params, listitem, True))
            
            listitem=xbmcgui.ListItem(offscreen=True)
            listitem.setLabel('[COLOR aqua][I]Choose page[/I][/COLOR]')
            
            
            
            listitem=xbmcgui.ListItem(offscreen=True)
            listitem.setLabel('[COLOR aqua][I]Next Page[/I][/COLOR]')
            if KODI_VERSION>19:
                info_tag = listitem.getVideoInfoTag()
                
                info_tag.setTitle('[COLOR aqua][I]Next Page[/I][/COLOR]')
            else:
                listitem.setInfo('Video', infoLabels={'title':'[COLOR aqua][I]Next Page[/I][/COLOR]'})
            listitem.setArt({'fanart':'https://static.bimago.pl/mediacache/catalog/product/cache/8/6/117168/image/750x1120/77f2bbb90b9f6398dc4944625b9e3c2c/117168_1.jpg','iconimage':'https://previews.123rf.com/images/alekseyvanin/alekseyvanin1801/alekseyvanin180100900/93405059-next-page-line-icon-outline-vector-sign-linear-style-pictogram-isolated-on-white-arrow-right-symbol-.jpg'})
            if 'page=' in self.url:
                link=self.url.split('page=')[0]
                page_no=self.url.split('page=')[1]
            else:
                link=self.url
                page_no='1'
            params={}
        
            params['description']=''
            params['url']=link+'page='+str(int(page_no)+1)
            params['name']='[COLOR aqua][I]Next Page[/I][/COLOR]'
           
            params['heb_name']='[COLOR aqua][I]Next Page[/I][/COLOR]'
            
            params['mode']=14
           
            
            params['eng_name']='[COLOR aqua][I]Next Page[/I][/COLOR]'
         

            url_params = f'{addon_id}/?' + urlencode(params) 
            
            self.all_lists.append((url_params, listitem, True))
        
        xbmcplugin .addDirectoryItems(int(sys.argv[1]),self.all_lists,len(self.all_lists))
        if self.tv_movie=='movie':
            xbmcplugin.setContent(int(sys.argv[1]), 'movies')
        else:
            if self.data_type=='seasons':
                xbmcplugin.setContent(int(sys.argv[1]), 'seasons')
            elif self.data_type=='episodes':
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
            else:
                xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
            
           
        #xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)
        log.warning(time.time()-start)
    def get_trakt_seasons(self,id):
        from  resources.modules.general import call_trakt
        self.all_tv_w={}
        self.all_w_tv_data={}
        self.all_tv_w_ep={}
        self.season_watched={}
        log.warning('trakt season')
        i = (call_trakt('/users/me/watched/shows?extended=full'))
  
        for ids in i:
            if str(ids['show']['ids']['tmdb'])==str(id):
                
             
             for seasons in ids['seasons']:
              count_episodes=0
              for ep in seasons['episodes']:
                
                count_episodes+=1
                
              self.season_watched[str(seasons['number'])]=count_episodes
        
    def fix_data_season(self,data,html,order,seasons,id):
             html_get=html.get
             
             
             
             data_get=data.get
             try:
               if 'first_air_date' in html:
                show_original_year=html['first_air_date'].split("-")[0]
               else:
                show_original_year=0
             except:
                show_original_year=0
        
             
             plot=html['overview']
             fanart=' '
             original_title=html['original_name']
             name=html['name']
             heb_name=name
             tmdbid=html['id']
             id=tmdbid
            
             if html['original_language']!='en':
               original_title=html['name']
             new_name=Addon.getLocalizedString(32101)+str(data['season_number'])
             if data['air_date']!=None:
                 year=str(data['air_date'].split("-")[0])
                 premired=data['air_date']
             else:
               year=0
               premired='0'
             
             season=str(data['season_number'])
             
             if data['poster_path']==None:
                icon=' '
             else:
               icon=data['poster_path']
             if 'backdrop_path' in data:
                 if data['backdrop_path']==None:
                  fan=fanart
                 else:
                  fan=data['backdrop_path']
             else:
                fan=html['backdrop_path']
             ep_number='0'
             if 'episode_count' in data:
                ep_number=data['episode_count']
             
             watched='no'
             
             
             if plot==None:
               plot=' '
             if fan==None:
               fan=fanart
             if 'http' not in fan:
               fan='https://image.tmdb.org/t/p/original/'+fan
             if 'http' not in icon:
               icon='https://image.tmdb.org/t/p/original/'+icon
             
             
             remain=''
              
             
             color='white'
             
             stop_data=False
             if str(data['season_number'])=='0' or str(data['season_number'])=='-1':
                stop_data=True
             watched='no'
             self.season_watched_marked[data.get('season_number',0)]='no'
             if str(data['season_number']) in str(self.season_watched):
                if int(self.season_watched[str(data.get('season_number',0))])>=int(seasons.get(data['season_number'],0)):
                    watched='yes'
                    self.season_watched_marked[data.get('season_number',0)]='yes'
             if not stop_data:
                 
                 url=f'https://api.themoviedb.org/3/tv/%s/season/%s?api_key={tmdb_key}&language=%s&append_to_response=external_ids'%(id,season,lang)
   
                 params={}
                 params['iconimage']=icon
                 params['fanart']=fan
                 params['description']=plot
                 params['url']=url
                 params['name']=new_name
                 params['image_master']=fan
                 params['heb_name']=heb_name
                 
                 params['data']=year
                 params['original_title']=original_title
                 params['id']=id
                 params['mode']=19
                 params['season']=season
                 params['episode']=' '
                 params['tmdbid']=tmdbid
                 params['eng_name']=original_title
                 params['show_original_year']=show_original_year
                 url_params = f'{addon_id}/?' + urlencode(params)
                 
                 
                 
                 season_data, total_seasons, total_aired_eps = html_get('seasons'),html_get('number_of_seasons'), data_get('episode_count')                 
                 
                 r_banner=''
                 r_back=''
                 r_art=''
                 r_logo=''
                 iconimage=icon
                 art={'fanart':fan,'iconimage':iconimage,'clearlogo':r_logo,'clearart':r_art,'icon': iconimage, 'thumb': fan, 'poster': iconimage,'tvshow.poster': iconimage, 'season.poster': iconimage,'banner': r_banner, 'landscape': r_back, 'discart': iconimage}
                 
                 data_pre={}
                 data_pre['art']=art
                 trailer = "%s?mode=25&id=%s&url=%s" % (addon_id,id,self.tv_movie)
                 
                 video_data={}
                 video_data['title']=new_name
                 video_data['plot']=plot
                 video_data['premiered']=premired
                 video_data['trailer']=trailer
                 video_data['OriginalTitle']=original_title
                 
                 self.all_d[season]={}
                 self.all_d[season]['url_params']=url_params
                 self.all_d[season]['video_data']=video_data
                 self.all_d[season]['data_pre']=data_pre
                 
                 self.all_d[season]['total_aired_eps']=total_aired_eps
                 self.all_d[season]['total_seasons']=total_seasons
                 self.all_d[season]['cast']=[]
                 self.all_d[season]['order']=order
                 self.all_d[season]['imdb_id']=''
                 
                
                 
                 
    def get_trd_season(self,html,seasons):
        
        id=html['id']
        if Addon.getSetting("trakt_access_token")!='' and Addon.getSetting("trakt_info")=='true':
            self.get_trakt_seasons(id)
        self.season_watched_marked={}
        with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                i=0
                for data in html['seasons']:
                    
                    futures.append(executor.submit(self.fix_data_season, data=data,html=html,order=i,seasons=seasons,id=id))
                    i+=1
                wait(futures)
        return self.all_d
    def get_seasons(self):
        html=cache.get(self.get_response,24,self.url, table='posters')
        seasons={}
        for data in html['seasons']:
            seasons[data['season_number']]=data['episode_count']
        #self.fix_data_season(data,html,1,seasons,html['id'])
        #self.all_d=self.get_trd_season(html)
        #self.fix_data_season(html['seasons'][0],html,1)
        self.all_d=cache.get(self.get_trd_season,24,html,seasons, table='posters')
        self.simple_data=True
        self.data_type='seasons'
        self.add_dir()
    def episode_items(self,data,heb_name,original_title,id,season,html,order):
         
         plot=data['overview']
         ep_name=''
         if 'name' in data and data['name']!=None:
            ep_name=data['name']
         else:
            ep_name='פרק '+str(count)
         
         new_name=str(data['episode_number'])+" . "+ep_name
         air_date=''
         if 'air_date' in data:
           if data['air_date']!=None:
             
             year=str(data['air_date'].split("-")[0])
           else:
             year=0
         else:
           year=0
         
         if data['still_path']!=None:
           if 'https' not in data['still_path']:
             fan='https://image.tmdb.org/t/p/original/'+data['still_path']
           else:
             fan=data['still_path']
           
         elif html['poster_path']!=None:
          if 'https' not in html['poster_path']:
             fan='https://image.tmdb.org/t/p/original/'+html['poster_path']
          else:
             fan=html['poster_path']
         else:
             fan=' '
         if html['poster_path']!=None:
          if 'https' not in html['poster_path']:
           icon='https://image.tmdb.org/t/p/original/'+html['poster_path']
          else:
            icon=html['poster_path']
         else:
           icon=iconimage
         try:duration=int(data.get('runtime', '90') * 60)
         except:duration = ''
         #if image2==fanart:
         #  icon=iconimage
          
         #  image=fanart
         color2='white'
         try:
            premired=' '
            if 'air_date' in data:
                   premired=data['air_date']
                   datea='[COLOR aqua]'+str(time.strptime(data['air_date'], '%Y-%m-%d'))+'[/COLOR]\n'
                   
                   a=(time.strptime(data['air_date'], '%Y-%m-%d'))
                   b=time.strptime(str(time.strftime('%Y-%m-%d')), '%Y-%m-%d')
                   
               
                   if a>b:
                     color2='red'
                   else:
                     
                     color2='white'
            datea='[COLOR gold]'+Addon.getLocalizedString(32187)+time.strftime( "%d-%m-%Y",a) + '[/COLOR]\n'
         except:
                 try:
                    datea=data['air_date']
                 except:
                    datea=''
                 color2='red'
         f_subs=[]
         

         color=color2
         
         tv_movie='tv'
         
         
         
           
         params={}
         params['iconimage']=icon
         params['fanart']=fan
         params['description']=plot
         params['url']='www'
         params['name']=new_name
         params['image_master']=fan
         params['heb_name']=heb_name
         
         params['data']=year
         params['original_title']=original_title
         params['id']=id
         params['mode']=15
         params['season']=season
         params['episode']=data['episode_number']
         params['tmdbid']=id
         params['eng_name']=original_title
         params['show_original_year']=year
         url_params = f'{addon_id}/?' + urlencode(params)
         
         
         
            
         
         r_banner=''
         r_back=''
         r_art=''
         r_logo=''
         iconimage=icon
         art={'fanart':fan,'iconimage':iconimage,'clearlogo':r_logo,'clearart':r_art,'icon': iconimage, 'thumb': fan, 'poster': iconimage,'tvshow.poster': iconimage, 'season.poster': iconimage,'banner': r_banner, 'landscape': r_back, 'discart': iconimage}
         
         data_pre={}
         data_pre['art']=art
         trailer = "%s?mode=25&id=%s&url=%s" % (addon_id,id,self.tv_movie)
         
         video_data={}
         video_data['title']=new_name
         video_data['plot']=plot
         video_data['premiered']=premired
         video_data['trailer']=trailer
         video_data['OriginalTitle']=original_title
         video_data['mediatype']='episode'
         video_data['TVshowtitle']=original_title
         video_data['Season']=int(str(season))
         video_data['Episode']=int(str(data['episode_number']))
          
         if premired!=' ':
            video_data['premiered']=premired
         self.all_d[data['episode_number']]={}
         self.all_d[data['episode_number']]['url_params']=url_params
         self.all_d[data['episode_number']]['video_data']=video_data
         self.all_d[data['episode_number']]['data_pre']=data_pre
         
         self.all_d[data['episode_number']]['total_aired_eps']=''
         self.all_d[data['episode_number']]['total_seasons']=''
         self.all_d[data['episode_number']]['cast']=[]
         self.all_d[data['episode_number']]['order']=order
         self.all_d[data['episode_number']]['imdb_id']=''
         self.all_d[data['episode_number']]['tmdb']=data.get('show_id','')
         return self.all_d
    def get_trd_episodes(self,html,season):
        with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                i=0
                for data in html['episodes']:
                    
                    futures.append(executor.submit(self.episode_items, data=data,heb_name=self.heb_name,original_title=self.original_title,id=self.id,season=season,html=html,order=i))
                    i+=1
                wait(futures)
        return self.all_d
    
    def get_episodes(self):
        html=cache.get(self.get_response,24,self.url, table='posters')
        season=str(html['season_number'])
        self.all_d=cache.get(self.get_trd_episodes,12,html,season, table='posters')
        
        '''
        i=0
        for data in html['episodes']:
            self.episode_items(data,self.heb_name,self.original_title,self.id,season,html,i)
            i+=1
        '''
        self.simple_data=True
        self.data_type='episodes'
        self.add_dir(season=season)
                 
                 
                 
                 