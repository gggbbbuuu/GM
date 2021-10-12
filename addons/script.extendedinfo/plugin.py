import sys
import xbmcgui, xbmcplugin
import requests,json,xbmcaddon,xbmcvfs
from resources.lib import process
from resources.lib import Utils
from resources.lib.library import addon_ID
from resources.lib.library import addon_ID_short

class Main:
	def __init__(self):
		xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
		self._parse_argv()
		log_urls = xbmcaddon.Addon(addon_ID()).getSetting('log_urls')
		for info in self.infos:
			listitems = process.start_info_actions(self.infos, self.params)
			xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_TITLE)
			xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
			xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_DURATION)

			if info.endswith('shows') or '=tv' in str(sys.argv):
				xbmcplugin.setContent(self.handle, 'tvshows')
			elif info.endswith('movies'):
				xbmcplugin.setContent(self.handle, 'movies')
			elif 'imdb_list' in str(info) or '=movie' in str(sys.argv):
				xbmcplugin.setContent(self.handle, 'movies')
			else:
				xbmcplugin.setContent(self.handle, 'addons')
			try:
				Utils.pass_list_to_skin(name=info, data=listitems, prefix=self.params.get('prefix', ''), handle=self.handle, limit=self.params.get('limit', ''))
			except:
				Utils.hide_busy()
				return
		else:
			items = [
				('popularmovies', 'Popular Movies'),
				('topratedmovies', 'Top Rated Movies'),
				('incinemamovies', 'In Theaters Movies'),
				('upcomingmovies', 'Upcoming Movies'),
				('libraryallmovies', 'My Movies (Library)'),
				('populartvshows', 'Popular TV Shows'),
				('topratedtvshows', 'Top Rated TV Shows'),
				('onairtvshows', 'Currently Airing TV Shows'),
				('airingtodaytvshows', 'Airing Today TV Shows'),
				('libraryalltvshows', 'My TV Shows (Library)')
				]
			NoFolder_items = [
				('allmovies', 'All Movies'),
				('alltvshows', 'All TV Shows'),
				('search_menu', 'Search...')
				]
			trakt_plugin_list = xbmcaddon.Addon(addon_ID()).getSetting('trakt_plugin_list')
			imdb_plugin_list = xbmcaddon.Addon(addon_ID()).getSetting('imdb_plugin_list')
			file_path = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path'))
			imdb_json = xbmcaddon.Addon(addon_ID()).getSetting('imdb_json')
			custom_imdb_json = xbmcaddon.Addon(addon_ID()).getSetting('custom_imdb_json')
			#https://raw.githubusercontent.com/henryjfry/repository.thenewdiamond/main/imdb_list.json
			if not '://' in str(imdb_json):
				json_file = open(imdb_json)
				data = json.load(json_file)
				json_file.close()
			elif str(imdb_json) != '' and custom_imdb_json == 'true':
				data = requests.get(imdb_json).json()
			else:
				imdb_json = file_path + 'imdb_list.json'
				json_file = open(imdb_json)
				data = json.load(json_file)
				json_file.close()

			NoFolder_items2 = [
				('allmovies', 'All Movies'),
				('alltvshows', 'All TV Shows'),
				]
			trakt_items = [
				('trakt_watched', 'Trakt Watched Movies'),
				('trakt_watched', 'Trakt Watched TV'),
				('trakt_progress', 'Trakt Shows Progress'),
				('trakt_coll', 'Trakt Collection Movies'),
				('trakt_coll', 'Trakt Collection TV'),
				('trakt_trend', 'Trakt Trending Shows'),
				('trakt_trend', 'Trakt Trending Movies'),
				('trakt_popular', 'Trakt Popular Shows'),
				('trakt_popular', 'Trakt Popular Movies'),
			]

			NoFolder_items2.append(('search_menu', 'Search...'))
			if imdb_plugin_list == 'true':
				for i in data['imdb_list']:
					list_name = (i[str(list(i)).replace('[\'','').replace('\']','')])
					list_number = (str(list(i)).replace('[\'','').replace('\']',''))
					new_list = ('imdb_list', [list_name, list_number])
					NoFolder_items2.append(new_list)

			NoFolder_items = NoFolder_items2

			#https://raw.githubusercontent.com/henryjfry/repository.thenewdiamond/main/trakt_list.json
			trakt_json = xbmcaddon.Addon(addon_ID()).getSetting('trakt_json')
			custom_trakt_json = xbmcaddon.Addon(addon_ID()).getSetting('custom_trakt_json')
			if not '://' in trakt_json:
				json_file = open(trakt_json)
				trakt_data = json.load(json_file)
				json_file.close()
			elif str(trakt_json) != '' and custom_trakt_json == 'true':
				trakt_data = requests.get(trakt_json).json()
			else:
				trakt_json = file_path + 'trakt_list.json'
				json_file = open(trakt_json)
				trakt_data = json.load(json_file)
				json_file.close()
			for i in trakt_data['trakt_list']:
				if str(i['name']) != '':
					trakt_items.append(('trakt_list', i['name']))

			xbmcplugin.setContent(self.handle, 'addons')
			urls = ''
			for key, value in NoFolder_items:
				thumb_path  = 'special://home/addons/'+str(addon_ID())+'/resources/skins/Default/media/tmdb/thumb.png'
				fanart_path = 'special://home/addons/'+str(addon_ID())+'/resources/skins/Default/media/tmdb/fanart.jpg'
				url = 'plugin://'+str(addon_ID())+'?info=%s' % key
				if key == 'imdb_list':
					url = 'plugin://'+str(addon_ID())+'?info=imdb_list&script=False&list=%s&list_name=%s' % (value[1], value[0])
					li = xbmcgui.ListItem(label=value[0])
					isFolder = True
				else:
					li = xbmcgui.ListItem(label=value)
					isFolder = False
				li.setArt({'thumb': thumb_path, 'fanart': fanart_path})
				urls +=  url.replace('&script=False','&script=True') + '\n'
				urls +=  'ActivateWindow(10025, "' + url + '",return)\n\n'
				xbmcplugin.addDirectoryItem(handle=self.handle, url=url, listitem=li, isFolder=isFolder)

			for key, value in items:
				thumb_path  = 'special://home/addons/'+str(addon_ID())+'/resources/skins/Default/media/tmdb/thumb.png'
				fanart_path = 'special://home/addons/'+str(addon_ID())+'/resources/skins/Default/media/tmdb/fanart.jpg'
				url = 'plugin://'+str(addon_ID())+'?info=%s&limit=0&script=False' % key
				li = xbmcgui.ListItem(label=value)
				li.setArt({'thumb': thumb_path, 'fanart': fanart_path})
				urls +=  url.replace('&script=False','&script=False') + '\n'
				urls +=  'ActivateWindow(10025, "' + url + '",return)\n\n'
				xbmcplugin.addDirectoryItem(handle=self.handle, url=url, listitem=li, isFolder=True)

			if trakt_plugin_list == 'true':
				for key, value in trakt_items:
					thumb_path  = 'special://home/addons/'+str(addon_ID())+'/resources/skins/Default/media/tmdb/thumb.png'
					fanart_path = 'special://home/addons/'+str(addon_ID())+'/resources/skins/Default/media/tmdb/fanart.jpg'
					script = 'False'
					if value == 'Trakt Watched Movies' or value == 'Trakt Collection Movies' or value == 'Trakt Trending Movies' or value == 'Trakt Popular Movies':
						trakt_type = 'movie'
					elif value == 'Trakt Watched TV' or value == 'Trakt Collection TV' or value == 'Trakt Trending Shows' or value == 'Trakt Popular Shows':
						trakt_type = 'tv'
					elif key == 'trakt_list':
						trakt_type = 'movie'
						for i in trakt_data['trakt_list']:
							if value == i['name']:
								user_id = i['user_id']
								list_slug = i['list_slug']
								trakt_sort_by = i['sort_by']
								trakt_sort_order = i['sort_order']
						url = 'plugin://'+str(addon_ID())+'?info='+str(key)+'&script=False&trakt_type=' +str(trakt_type)+'&list_slug='+str(list_slug)+'&user_id=' +str(user_id)+'&trakt_sort_by='+str(trakt_sort_by)+'&trakt_sort_order='+str(trakt_sort_order)+'&trakt_list_name='+str(value)
					#url = 'plugin://'+str(addon_ID())+'?info=%s&script=False&trakt_type=%s' % key, trakt_type
					if key != 'trakt_list':
						url = 'plugin://'+str(addon_ID())+'?info='+str(key)+'&script=False&trakt_type=' +str(trakt_type)
					li = xbmcgui.ListItem(label=value)
					li.setArt({'thumb': thumb_path, 'fanart': fanart_path})
					urls +=  url.replace('&script=False','&script=True') + '\n'
					urls +=  'ActivateWindow(10025, "' + url + '",return)\n\n'
					xbmcplugin.addDirectoryItem(handle=self.handle, url=url, listitem=li, isFolder=True)
			if log_urls == 'true':
				urls =  '\n' + urls
				xbmc.log('DIAMONDINFO_URLS=====>\n'+str(urls)+'===>DIAMONDINFO_URLS', level=xbmc.LOGINFO)
			Utils.hide_busy()
			xbmcplugin.endOfDirectory(self.handle)
		xbmcgui.Window(10000).clearProperty(str(addon_ID_short())+'_running')

	def _parse_argv(self):
		args = sys.argv[2][1:]
		self.handle = int(sys.argv[1])
		self.infos = []
		self.params = {'handle': self.handle}
		if args.startswith('---'):
			delimiter = '&'
			args = args[3:]
		else:
			delimiter = '&'
		for arg in args.split(delimiter):
			param = arg.replace('"', '').replace("'", " ")
			if param.startswith('info='):
				self.infos.append(param[5:])
			else:
				try:
					self.params[param.split('=')[0].lower()] = '='.join(param.split('=')[1:]).strip()
				except:
					pass

if (__name__ == '__main__'):
	Main()
	del Main
	del sys
	del xbmcgui
	del xbmcplugin
	del requests
	del json
	del xbmcaddon
	del xbmcvfs
	del process
	del Utils
	del addon_ID
	del addon_ID_short
