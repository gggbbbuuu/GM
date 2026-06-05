import re,xbmcaddon,xbmcgui
import requests,xbmc
import sys
from sys import exit as sysexit
from threading import Thread
from resources.modules import log
from urllib.parse import unquote, unquote_plus, quote
import time
import os
import xbmcvfs

import qrcode
HAS_QRCODE = True
global play_status_rd
play_status_rd=''

base_url = 'https://api.torbox.app/v1/api'
oauth_url = 'https://tor.box'
timeout = 10.0
session = requests.Session()
session.mount(base_url, requests.adapters.HTTPAdapter(max_retries=1))
from  resources.modules.client import get_html

global close_qr_now
close_qr_now = False

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
    def __init__(self, api_key=None):
        # ====== PERFORMANCE: Accept cached API key to avoid Addon.getSetting() call ======
        if api_key is not None:
            self.api_key = api_key
        else:
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
            # Delete torrent immediately after getting link (like Real Debrid)
            play_status_rd="Delete torrent"
            self.delete_torrent(torrent_id)
            return file_link
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
            return None

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

    def show_qr_dialog(self, qr_image_path, auth_code, url):
        """Display QR code in Kodi dialog similar to telemedia"""
        global close_qr_now
        try:
            from resources.modules import pyxbmct
            
            class QRDialog(pyxbmct.AddonDialogWindow):
                def __init__(self, title, qr_image_path, auth_code, url):
                    global close_qr_now
                    super(QRDialog, self).__init__(title)
                    close_qr_now = False
                    
                    self.setGeometry(600, 400, 5, 2, pos_x=300, pos_y=150)
                    self.qr_image_path = qr_image_path
                    self.auth_code = auth_code
                    self.url = url
                    self.set_active_controls()
                    self.set_navigation()
                    
                    # Connect back button to close
                    self.connect(pyxbmct.ACTION_NAV_BACK, self.close_dialog)
                    
                    # Auto-close after timeout
                    Thread(target=self.check_close).start()
                
                def check_close(self):
                    global close_qr_now
                    counter = 6000  # 10 minutes (600 seconds)
                    while close_qr_now == False and counter > 0:
                        xbmc.sleep(100)
                        counter -= 1
                    self.close()
                
                def close_dialog(self):
                    global close_qr_now
                    close_qr_now = True
                    self.close()
                
                def set_active_controls(self):
                    # QR code image
                    image = pyxbmct.Image(self.qr_image_path)
                    self.placeControl(image, 0, 0, rowspan=3, columnspan=1)
                    
                    # Auth code label
                    code_label = pyxbmct.Label(f'[B]Code: [COLOR deepskyblue]{self.auth_code}[/COLOR][/B]\n Code was copied to the clipboard')
                    self.placeControl(code_label, 3, 0)
                    
                    # URL label
                    url_label = pyxbmct.Label(f'[B]Visit: [COLOR yellow]{self.url}[/COLOR][/B]')
                    self.placeControl(url_label, 4, 0)
                    
                    # Close button
                    self.close_button = pyxbmct.Button('Close')
                    self.placeControl(self.close_button, 4, 1)
                    self.setFocus(self.close_button)
                    
                    # Connect close button
                    self.connect(self.close_button, self.close_dialog)
                
                def set_navigation(self):
                    self.close_button.controlUp(self.close_button)
                    self.close_button.controlDown(self.close_button)
            
            dialog = QRDialog('TorBox - Scan QR Code', qr_image_path, auth_code, url)
            dialog.doModal()
            del dialog
        except Exception as e:
            log.warning(f'QR dialog error: {str(e)}')
            # Fallback to simple OK dialog with code
            xbmcgui.Dialog().ok(
                'TorBox Authorization',
                f'[B]Code: [COLOR deepskyblue]{auth_code}[/COLOR][/B]\n'
                f'Visit: {url}'
            )

    def user_cloud_clear(self):
        if not xbmcgui.Dialog().yesno("TorBox", "בטוח?", "Cancel", "Ok"): return
        data = {'all': True, 'operation': 'delete'}
        self._POST(self.remove, json=data)
        self.clear_cache()

    def auth(self):
        """OAuth device code flow authentication - no manual option"""
        global close_qr_now
        Addon = xbmcaddon.Addon()
        
        try:
            # Step 1: Request device code using correct TorBox API endpoint
            user_agent_str = 'Mando'
            params = {'app': user_agent_str}
            response = requests.get(f'{base_url}/user/auth/device/start', params=params, timeout=timeout)
            
            if response.status_code != 200:
                log.warning(f'TorBox OAuth init failed: HTTP {response.status_code}')
                xbmcgui.Dialog().ok('TorBox Error', f'Server returned error: {response.status_code}')
                return False
            
            try:
                device_response = response.json()
            except:
                log.warning(f'TorBox OAuth init failed: Invalid JSON response')
                xbmcgui.Dialog().ok('TorBox Error', 'Invalid response from server')
                return False
            
            if 'data' not in device_response:
                log.warning(f'TorBox OAuth: Missing data in response')
                xbmcgui.Dialog().ok('TorBox Error', 'Invalid response from server')
                return False
            
            data = device_response['data']
            auth_code = data.get('code')
            device_code = data.get('device_code')
            interval = data.get('interval', 5)
            verification_url = data.get('verification_url', 'https://torbox.app/link')
            friendly_url = data.get('friendly_verification_url', verification_url)
            
            if not auth_code or not device_code:
                log.warning(f'TorBox OAuth: Missing code or device_code')
                xbmcgui.Dialog().ok('TorBox Error', 'Invalid response from server')
                return False
            
            # Generate QR code image
            user_dataDir = xbmcvfs.translatePath(Addon.getAddonInfo("profile"))
            qr_image_path = os.path.join(user_dataDir, "torbox_qr.png")
            
            try:
                img = qrcode.make(verification_url)
                img.save(qr_image_path)
                log.warning(f'QR code saved to: {qr_image_path}')
            except Exception as e:
                log.warning(f'Failed to generate QR code: {str(e)}')
                qr_image_path = None
            
            # Copy code to clipboard
            try:
                import subprocess
                if sys.platform == 'win32':
                    subprocess.check_call(f'echo {auth_code}|clip', shell=True)
                elif sys.platform.startswith('linux'):
                    from subprocess import Popen, PIPE
                    p = Popen(['xsel', '-pi'], stdin=PIPE)
                    p.communicate(input=auth_code.encode())
            except:
                pass
            dp=None
            # Show QR code in Kodi dialog
            if qr_image_path and os.path.exists(qr_image_path):
                # Start QR dialog in background thread
                close_qr_now = False
                Thread(target=self.show_qr_dialog, args=(qr_image_path, auth_code, friendly_url)).start()
                xbmc.sleep(500)  # Give dialog time to open
                #self.show_qr_dialog(qr_image_path, auth_code, friendly_url)
            else:
                # Show dialog with instructions
                dp = xbmcgui.DialogProgress()
                dp.create(
                    'TorBox OAuth',
                    f'[B]Code: [COLOR deepskyblue]{auth_code}[/COLOR][/B]\n'
                    f'Visit: [COLOR deepskyblue]{friendly_url}[/COLOR]\n'
                    f'[I]Waiting for authorization...[/I]'
                )
            
            # Step 2: Poll for authorization
            timeout_seconds = 600  # 10 minutes
            elapsed = 0
            api_token = None
            
            while elapsed < timeout_seconds:
                if dp and dp.iscanceled():
                    dp.close()
                    return False
                
                # Update progress
                progress = int((elapsed / timeout_seconds) * 100)
                remaining_mins = (timeout_seconds - elapsed) // 60
                remaining_secs = (timeout_seconds - elapsed) % 60
                if dp:
                    dp.update(
                        progress,
                        f'[B]Code: [COLOR deepskyblue]{auth_code}[/COLOR][/B]\n'
                        f'Visit: [COLOR deepskyblue]{friendly_url}[/COLOR]\n'
                        f'Time remaining: {remaining_mins:02d}:{remaining_secs:02d}'
                    )
                
                # Check if authorized
                try:
                    poll_data = {'device_code': device_code}
                    check_resp = requests.post(
                        f'{base_url}/user/auth/device/token',
                        json=poll_data,
                        timeout=timeout
                    )
                    
                    if check_resp.status_code == 200:
                        try:
                            check_response = check_resp.json()
                            if 'data' in check_response and 'access_token' in check_response['data']:
                                api_token = check_response['data']['access_token']
                                close_qr_now = True
                                break
                        except:
                            log.warning(f'TorBox OAuth check: Invalid JSON')
                except Exception as e:
                    log.warning(f'TorBox OAuth check error: {e}')
                
                # Wait before next check
                for _ in range(interval):
                    if dp and dp.iscanceled():
                        dp.close()
                        return False
                    xbmc.sleep(1000)
                
                elapsed += interval
            if dp:
                dp.close()
            
            # Close QR dialog
            close_qr_now = True
            
            if not api_token:
                xbmcgui.Dialog().ok('TorBox', 'Authorization timeout or failed. Please try again.')
                return False
            
            # Verify the API key works
            self.api_key = api_token
            user_info = self._GET('/user/me')
            if user_info and 'data' in user_info:
                customer = user_info['data']['customer']
                Addon.setSetting('tb.token', api_token)
                Addon.setSetting('tb.account_id', customer)
                xbmc.executebuiltin((u'Notification(%s,%s)' % ('Mando','%s %s' % ("Success", "Successfully authorized!"))))
                
                return True
            else:
                xbmcgui.Dialog().ok('TorBox Error', 'Failed to verify API key')
                return False
            
        except Exception as e:
            log.warning(f'TorBox OAuth error: {e}')
            xbmcgui.Dialog().ok('TorBox Error', f'Authentication failed: {str(e)}')
            return False

    def revoke_auth(self):
        Addon = xbmcaddon.Addon()
        if not xbmcgui.Dialog().yesno("TorBox", "בטוח?", "Cancel", "Ok"): return
        Addon.setSetting('tb.token', '')
        Addon.setSetting('tb.account_id', '')
        xbmc.executebuiltin((u'Notification(%s,%s)' % ('Mando','%s %s' % ("Success", "Revoke Authorization"))))
        

    

