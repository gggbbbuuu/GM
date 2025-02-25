#based on POV addon - Thanks
import re,xbmcaddon,xbmcgui
import requests,xbmc
from sys import exit as sysexit
from threading import Thread
from resources.modules import log
from urllib.parse import unquote, unquote_plus
global play_status_rd
play_status_rd=''

base_url = 'https://api.torbox.app/v1/api'
timeout = 10.0
session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))
from  resources.modules.client import get_html

def seas_ep_filter(season, episode, release_title, split=False, return_match=False):
        str_season, str_episode = str(season), str(episode)
        season_fill, episode_fill = str_season.zfill(2), str_episode.zfill(2)
        str_ep_plus_1, str_ep_minus_1 = str(episode+1), str(episode-1)
        release_title = re.sub(r'[^A-Za-z0-9-]+', '.', unquote(release_title).replace('\'', '')).lower()
        string1 = r'(s<<S>>[.-]?e[p]?[.-]?<<E>>[.-])'
        string2 = r'(season[.-]?<<S>>[.-]?episode[.-]?<<E>>[.-])|([s]?<<S>>[x.]<<E>>[.-])'
        string3 = r'(s<<S>>e<<E1>>[.-]?e?<<E2>>[.-])'
        string4 = r'([.-]<<S>>[.-]?<<E>>[.-])'
        string5 = r'(episode[.-]?<<E>>[.-])'
        string6 = r'([.-]e[p]?[.-]?<<E>>[.-])'
        string7 = r'(^(?=.*\.e?0*<<E>>\.)(?:(?!((?:s|season)[.-]?\d+[.-x]?(?:ep?|episode)[.-]?\d+)|\d+x\d+).)*$)'
        string_list = []
        string_list_append = string_list.append
        string_list_append(string1.replace('<<S>>', season_fill).replace('<<E>>', episode_fill))
        string_list_append(string1.replace('<<S>>', str_season).replace('<<E>>', episode_fill))
        string_list_append(string1.replace('<<S>>', season_fill).replace('<<E>>', str_episode))
        string_list_append(string1.replace('<<S>>', str_season).replace('<<E>>', str_episode))
        string_list_append(string2.replace('<<S>>', season_fill).replace('<<E>>', episode_fill))
        string_list_append(string2.replace('<<S>>', str_season).replace('<<E>>', episode_fill))
        string_list_append(string2.replace('<<S>>', season_fill).replace('<<E>>', str_episode))
        string_list_append(string2.replace('<<S>>', str_season).replace('<<E>>', str_episode))
        string_list_append(string3.replace('<<S>>', season_fill).replace('<<E1>>', str_ep_minus_1.zfill(2)).replace('<<E2>>', episode_fill))
        string_list_append(string3.replace('<<S>>', season_fill).replace('<<E1>>', episode_fill).replace('<<E2>>', str_ep_plus_1.zfill(2)))
        string_list_append(string4.replace('<<S>>', season_fill).replace('<<E>>', episode_fill))
        string_list_append(string4.replace('<<S>>', str_season).replace('<<E>>', episode_fill))
        string_list_append(string5.replace('<<E>>', episode_fill))
        string_list_append(string5.replace('<<E>>', str_episode))
        string_list_append(string6.replace('<<E>>', episode_fill))
        string_list_append(string7.replace('<<E>>', episode_fill))
        final_string = '|'.join(string_list)
        reg_pattern = re.compile(final_string)
        if split: return release_title.split(re.search(reg_pattern, release_title).group(), 1)[1]
        elif return_match: return re.search(reg_pattern, release_title).group()
        else: return bool(re.search(reg_pattern, release_title))
def extras_filter():
    return ('sample', 'extra', 'extras', 'deleted', 'unused', 'footage', 'inside', 'blooper', 'bloopers', 'making.of', 'feature',
            'featurette', 'behind.the.scenes', 'trailer')
def supported_video_extensions():
        supported_video_extensions = xbmc.getSupportedMedia('video').split('|')
        return [i for i in supported_video_extensions if not i in ('','.zip')]
        
class TorBoxAPI:
    download = '/torrents/requestdl'
    remove = '/torrents/controltorrent'
    stats = '/user/me'
    history = '/torrents/mylist'
    explore = '/torrents/mylist?id=%s'
    cache = '/torrents/checkcached'
    cloud = '/torrents/createtorrent'
    t_info='/torrents/torrentinfo'
    def __init__(self):
        Addon = xbmcaddon.Addon()
        self.api_key = Addon.getSetting('tb.token')

    def _request(self, method, path, params=None, json=None, data=None):
        if not self.api_key: return
        
        session.headers['Authorization'] = 'Bearer %s' % self.api_key
        full_path = '%s%s' % (base_url, path)

        
        #r=get_html(full_path,headers=headers,params=params, json=json, data=data, timeout=timeout,post=method=='post')
        r = session.request(method, full_path, params=params, json=json, data=data, timeout=timeout)
        try: r.raise_for_status()
        except Exception as e: log.warning('torbox error: '+ f"{e}\n{r.json()}")
        try: r = r.json()
        except: r = {}
        return r

    def _GET(self, url, params=None):
        return self._request('get', url, params=params)

    def _POST(self, url, params=None, json=None, data=None):
        return self._request('post', url, params=params, json=json, data=data)

    def account_info(self):
        return self._GET(self.stats)

    def user_cloud(self):
        
        url = self.history
        return cache.get(self._GET,24,url, table='pages') 

    def user_cloud_info(self, request_id=''):
       
        url = self.explore % request_id
        return cache.get(self._GET,24,url, table='pages')  

    def torrent_info(self, request_id=''):
        url = self.explore % request_id
        return self._GET(url)

    def delete_torrent(self, request_id=''):
        data = {'torrent_id': request_id, 'operation': 'delete'}
        return self._POST(self.remove, json=data)

    def unrestrict_link(self, file_id):
        torrent_id, file_id = file_id.split(',')
        params = {'token': self.api_key, 'torrent_id': torrent_id, 'file_id': file_id}
        try: return self._GET(self.download, params=params)['data']
        except: return None

    def add_magnet(self, magnet):
        data = {'magnet': magnet, 'seed': 3, 'allow_zip': False}
        return self._POST(self.cloud, data=data)

    def check_cache_single(self, hash):
        return self._GET(self.cache, params={'hash': hash, 'format': 'list'})

    def check_cache(self, hashlist):
        data = {'hashes': hashlist}
     
        return self._POST(self.cache, params={'format': 'list','list_files':True}, json=data)
    def get_torrentinfo(self,hash):
        return self._GET(self.t_info, params={'hash': hash, 'timeout': timeout})
    def create_transfer(self, magnet_url):
        result = self.add_magnet(magnet_url)
        if not result['success']: return 'failed'
        return result
    
    def resolve_magnet(self, magnet_url, info_hash, store_to_cloud, title, season, episode):
        global play_status_rd
        play_status_rd="Start (1/4)"
        try:
            season=int(season)
            episode=int(episode)
        except:
            season=None
            episode=None
        
        try:
            file_url, match = None, False
            extensions = supported_video_extensions()
            extras_filtering_list = extras_filter()
            play_status_rd="Check Hash  (2/4)"
            check = self.check_cache_single(info_hash)
            
            match = info_hash in [i['hash'] for i in check['data']]
   
            if not match: return None
  
            play_status_rd="Add Magnet  (3/4)"
            torrent = self.add_magnet(magnet_url)
   
            if not torrent['success']: return None
            torrent_id = torrent['data']['torrent_id']
            torrent_files = self.torrent_info(torrent_id)
            torrent_files = [(i['id'], i['short_name'], i['size']) for i in torrent_files['data']['files']]
            vid_only = [item for item in torrent_files if item[1].lower().endswith(tuple(extensions))]
            remainder = [i for i in torrent_files if i not in vid_only]
            torrent_files = vid_only + remainder
            if not torrent_files: return None
            if season:
                torrent_files = [i for i in torrent_files if seas_ep_filter(season, episode, i[1])]
                if not torrent_files: return None
            else:
                if self._m2ts_check(torrent_files): self.delete_torrent(torrent_id) ; return None
                else: torrent_files.sort(key=lambda k: k[2], reverse=True)
            file_key = [i[0] for i in torrent_files if not any(x in i[1] for x in extras_filtering_list)][0]
            play_status_rd="Unrestrict link  (4/4)"
            file_link = self.unrestrict_link('%d,%d' % (torrent_id, file_key))
            
            return file_link,torrent_id
        except Exception as e:
            import linecache,sys
            break_window=True
            exc_type, exc_obj, tb = sys.exc_info()
            f = tb.tb_frame
            lineno = tb.tb_lineno
            filename = f.f_code.co_filename
            linecache.checkcache(filename)
            line = linecache.getline(filename, lineno, f.f_globals)
          
            log.warning('ERROR IN TorBox:'+str(lineno))
            log.warning('inline:'+line)
            log.warning(e)
            if torrent_id: self.delete_torrent(torrent_id)
            return None,None

    def display_magnet_pack(self, magnet_url, info_hash):
       
        try:
            extensions = supported_video_extensions()
            torrent = self.add_magnet(magnet_url)
            if not torrent['success']: return None
            torrent_id = torrent['data']['torrent_id']
            torrent_files = torrent_files = self.torrent_info(torrent_id)
            torrent_files = [(i['id'], i['short_name'], i['size']) for i in torrent_files['data']['files']]
            end_results = []
            append = end_results.append
            for item in torrent_files:
                if item[1].lower().endswith(tuple(extensions)):
                    append({'link': '%d,%d' % (torrent_id, item[0]), 'filename': item[1], 'size': item[2]})
            #self.delete_torrent(torrent_id) # untested if link will play if torrent deleted
            return end_results
        except Exception:
            if torrent_id: self.delete_torrent(torrent_id)
            return None



    def _m2ts_check(self, folder_items):
        for item in folder_items:
            if item[1].endswith('.m2ts'): return True
        return False

    def user_cloud_clear(self):
        if not xbmcgui.Dialog().yesno("TorBox", "בטוח?", "Cancel", "Ok"): return
        data = {'all': True, 'operation': 'delete'}
        self._POST(self.remove, json=data)
        self.clear_cache()

    def auth(self):
        Addon = xbmcaddon.Addon()
        api_key = xbmcgui.Dialog().input('TorBox API Key:')
        if not api_key: return
        self.api_key = api_key
        r = self._GET('/user/me')
        customer = r['data']['customer']
        Addon.setSetting('tb.token', api_key)
        Addon.setSetting('tb.account_id', customer)
        xbmc.executebuiltin((u'Notification(%s,%s)' % ('Mando','%s %s' % ("Success", 'TorBox'))))
        
        return True

    def revoke_auth(self):
        Addon = xbmcaddon.Addon()
        if not xbmcgui.Dialog().yesno("TorBox", "בטוח?", "Cancel", "Ok"): return
        Addon.setSetting('tb.token', '')
        Addon.setSetting('tb.account_id', '')
        xbmc.executebuiltin((u'Notification(%s,%s)' % ('Mando','%s %s' % ("Success", "Revoke Authorization"))))
        

    

