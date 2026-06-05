# -*- coding: utf-8 -*-

import time,xbmc,logging,json,builtins

from  resources.modules.client import get_html
from resources.modules import log

class AllDebrid:
    
    def __init__(self):
        from  resources.modules import tools
        self.tools=tools
        self.agent_identifier = self.tools.addonName
        self.token = self.tools.getSetting('alldebrid.token')
        self.base_url = 'https://api.alldebrid.com/v4.1/'
        #if self.token=='':
        #    self.auth()
        

    def get_url(self, url, token_req=False):
     
        if  self.token == '':
            return

        url = '{}{}'.format(self.base_url, url)

        if not '?' in url:
            url += '?'
            url += 'agent={}'.format(self.agent_identifier)
        else:
            url += '&agent={}'.format(self.agent_identifier)

        if token_req:
            url += '&apikey={}'.format(self.token)
  
        return get_html(url).json()

    def post_url(self, url, post_data=None, token_req=False):

        if  self.token == '':
            return

        url = '{}{}'.format(self.base_url, url)

        if not '?' in url:
            url += '?'
            url += 'agent={}'.format(self.agent_identifier)
        else:
            url += '&agent={}'.format(self.agent_identifier)

        if token_req:
            url += '&apikey={}'.format(self.token)
        
        a=get_html(url, data=post_data).json()
        
        return a

    def auth(self):
        pin_url = '{}pin/get?agent={}'.format(self.base_url.replace('4.1','4'), self.agent_identifier)
        resp = get_html(pin_url).json()['data']
       
        expiry = pin_ttl = int(resp['expires_in'])
       
        auth_complete = False
        self.tools.copy2clip(resp['pin'])

        self.tools.progressDialog.create('{} - {}'.format(self.tools.addonName, 'AllDebrid Auth'))
        self.tools.progressDialog.update(100, 'Open this link in a browser: {}'.format(self.tools.colorString(resp['base_url']))+'\n'+
                                    'Enter the code: {}'.format(self.tools.colorString(
                                        resp['pin']))+'\n'+
                                    'This code has been copied to your clipboard')

        # Seems the All Debrid servers need some time do something with the pin before polling
        # Polling to early will cause an invalid pin error
        time.sleep(5)

        while not auth_complete and not expiry <= 0 and not self.tools.progressDialog.iscanceled():
       
            auth_complete, expiry = self.poll_auth(resp['check_url'])
            progress_percent = 100 - int((float(pin_ttl - expiry) / pin_ttl) * 100)
            self.tools.progressDialog.update(progress_percent)
            time.sleep(1)

        try:self.tools.progressDialog.close()
        except:pass

        self.store_user_info()

        if auth_complete:
            xbmc.executebuiltin((u'Notification(%s,%s)' % (self.tools.addonName, ('Authentication is completed'))))
            
        else:
            return

    def poll_auth(self, poll_url):

        resp = get_html(poll_url).json()['data']
        if resp['activated']:
           
            self.tools.setSetting('alldebrid.token', resp['apikey'])
            self.token = resp['apikey']
            return True, 0

        return False, int(resp['expires_in'])


    def store_user_info(self):
        user_information = self.get_url('user', True)
       
        self.tools.setSetting('alldebrid.username', user_information['data']['user']['username'])
        return

    def check_hash(self, hash_list):
        all_mag=[]
        for itt in hash_list:
            all_mag.append(itt)
        post_data = {'magnets[]': hash_list}
        return self.get_url('magnet/instant?magnets[]='+'&magnets[]='.join(all_mag), token_req=True)
        
        return self.post_url('magnet/instant', post_data, True)

    def upload_magnet(self, hash):
        return self.get_url('magnet/upload?magnet={}'.format(hash), token_req=True)

    def update_relevant_hosters(self):
        return self.get_url('hosts')

    def get_hosters(self, hosters):
        import database
        host_list = database.get(self.update_relevant_hosters, 1)
        if host_list is None:
            host_list = self.update_relevant_hosters()
        if host_list is not None:
            hosters['premium']['all_debrid'] = [(i['domain'], i['domain'].split('.')[0])
                                                for i in host_list['hosts'] if i['status']]
            hosters['premium']['all_debrid'] += [(host, host.split('.')[0])
                                                for i in host_list['hosts'] if 'altDomains' in i and i['status']
                                                for host in i['altDomains']]
        else:
            import traceback
            traceback.print_exc()
            hosters['premium']['all_debrid'] = []

    def resolve_hoster(self, url):
        url = self.tools.quote(url)
        resolve = self.get_url('link/unlock?link={}'.format(url), token_req=True)
      
        if resolve['status']=='success':
            return resolve['data']['link']
        else:
            return None

    def magnet_status(self, magnet_id):
        return self.get_url('magnet/status?id={}'.format(magnet_id), token_req=True)
    
    def _flatten_files(self, files):
        """Recursively flatten nested file structure from AllDebrid API"""
        flattened = []
        for item in files:
            if 'e' in item:  # Item is a folder/container with entries
                flattened.extend(self._flatten_files(item['e']))
            else:  # Item is a file
                flattened.append(item)
        return flattened

    def movie_magnet_to_stream(self, magnet,season,episode,tv_movie):
        selectedFile = None

        magnet_id = self.upload_magnet(magnet)

       
        if 'error' in magnet_id:
          
            return None
        
        # Extract magnet ID from response
        magnets = magnet_id.get('data', {}).get('magnets', [])
        log.warning(f"magnet upload response: {magnet_id}")
        if not magnets:
            
            return None
        magnet_id = magnets[0]['id']
        all_lk=(self.magnet_status(magnet_id))

        
        # Check if magnet is ready and has files
        magnet_data = all_lk.get('data', {}).get('magnets', {})
        if magnet_data.get('status') != 'Ready' or 'files' not in magnet_data:
           
            self.delete_magnet(magnet_id)
            return None
        log.warning(f"magnet_data:{magnet_data}")
        links = self._flatten_files(magnet_data['files'])
        extensions=['mkv','avi','mp4']
        valid_results = [i for i in links if any(i.get('n').lower().endswith(x) for x in extensions) and i.get('l', '')]

        if not valid_results:
        
            self.delete_magnet(magnet_id)
            return None
            
        if (tv_movie=='movie'):
            selectedFile = builtins.max(valid_results, key=lambda x: x.get('s')).get('l', None)
           
        else:
            # Format season and episode for matching (handle both "4" and "04" formats)
            season_str = str(int(season)).zfill(2)  # "4" -> "04"
            episode_str = str(int(episode)).zfill(2)  # "1" -> "01"
            season_no_pad = str(int(season))  # "4"
            episode_no_pad = str(int(episode))  # "1"
            
            for items in valid_results:
                test_name = items['n'].lower()

                
                # Check for episode patterns: s04e01, s4e1, etc.
                episode_patterns = [
                    f's{season_str}e{episode_str}.',
                    f's{season_str}e{episode_str} ',
                    f's{season_no_pad}e{episode_no_pad}.',
                    f's{season_no_pad}e{episode_no_pad} ',
                    f's{season_str}e{episode_no_pad}.',
                    f's{season_no_pad}e{episode_str}.',
                    f'ep {episode_str}',
                    f'ep {episode_no_pad}',
                    f'{season_no_pad}x{episode_str}',
                    f'{season_no_pad}x{episode_no_pad}'
                ]
                
                if any(pattern in test_name for pattern in episode_patterns):
                    if any(test_name.endswith(ext) for ext in ['mkv', 'avi', 'mp4']):
                        selectedFile = items['l']
                        break
                        
        self.delete_magnet(magnet_id)
        if selectedFile == None:
            return None
        return self.resolve_hoster(selectedFile)

    def resolve_magnet(self, magnet, args, torrent, pack_select=False):
        import source_utils
        if 'showInfo' not in args:
            return self.movie_magnet_to_stream(magnet, args)

        magnet_response = self.upload_magnet(magnet)
        if 'error' in magnet_response:
            log.warning(f"upload_magnet error: {magnet_response['error']}")
            return None
            
        magnets = magnet_response.get('data', {}).get('magnets', [])
        if not magnets:
            log.warning("No magnet data in response")
            return None
        magnet_id = magnets[0]['id']

        episodeStrings, seasonStrings = source_utils.torrentCacheStrings(args)

        try:
            folder_details = self.magnet_status(magnet_id)

            if folder_details['status'] != 'Ready':
                return

            folder_details = [{'link': key, 'filename': value}
                              for key, value in folder_details['links'].items()]


            if 'extra' not in args['info']['title'] and 'extra' not in args['showInfo']['info']['tvshowtitle'] \
                    and int(args['info']['season']) != 0:
                folder_details = [i for i in folder_details if
                                  'extra' not in
                                  source_utils.cleanTitle(i['filename'].replace('&', ' ').lower())]

            if 'special' not in args['info']['title'] and 'special' not in args['showInfo']['info']['tvshowtitle'] \
                    and int(args['info']['season']) != 0:
                folder_details = [i for i in folder_details if
                                  'special' not in
                                  source_utils.cleanTitle(i['filename'].replace('&', ' ').lower())]

            streamLink = self.check_episode_string(folder_details, episodeStrings)

            if streamLink is None:
                return

            self.delete_magnet(magnet_id)

            return self.resolve_hoster(streamLink)
        except:
            import traceback
            traceback.print_exc()
            pass

    def check_episode_string(self, folder_details, episodeStrings):
        import source_utils
        for i in folder_details:
            for epstring in episodeStrings:
                if epstring in source_utils.cleanTitle(i['filename'].replace('&', ' ').lower()):
                    if any(i['filename'].endswith(ext) for ext in source_utils.COMMON_VIDEO_EXTENSIONS):
                        return i['link']
        return None

    def delete_magnet(self, magnet_id):
        return self.get_url('magnet/delete?id={}'.format(magnet_id), token_req=True)