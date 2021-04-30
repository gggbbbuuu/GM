from resources.lib.modules.addon import Addon
import sys,os
import xbmc
import xbmcvfs
if sys.version_info[0] == 3:
	from urllib.parse import urlparse, parse_qs, urlencode
else:
	import urlparse
	from urllib import urlencode

import sys
import xbmc, xbmcgui, xbmcplugin, xbmcaddon
from resources.lib.modules import control, cache, constants
from resources.lib.modules.log_utils import log

addon = Addon('plugin.video.apex_sports', sys.argv)
addon_handle = int(sys.argv[1])

if not os.path.exists(control.dataPath):
	os.mkdir(control.dataPath)

AddonPath = control.addonPath
IconPath = os.path.join(AddonPath, control.transPath("resources/media/"))
fanart = os.path.join(AddonPath, control.transPath("/fanart.jpg"))

def icon_path(filename):
	if 'http' in filename:
		return filename
	return control.transPath(os.path.join(IconPath, filename))

try:
	from urllib.parse import urlparse, parse_qs
	args = parse_qs(sys.argv[2][1:])
except:
	args = urlparse.parse_qs(sys.argv[2][1:])

mode = args.get('mode', None)
if mode is None:
	if control.setting('disable_live_sport') == 'false':
		addon.add_item({'mode': 'open_category', 'category':'live_sport'}, {'label': 'Live Sport', 'title':'Live Sport'}, img=icon_path('live_sport.jpg'), fanart=fanart, is_folder=True)
	if control.setting('disable_live_tv') == 'false':
		addon.add_item({'mode': 'open_category', 'category': 'live_tv'}, {'label': 'Live TV', 'title':'Live TV'}, img=icon_path('live_tv.jpg'), fanart=fanart, is_folder=True)
	if control.setting('disable_replays') == 'false':
		addon.add_item({'mode': 'open_category', 'category': 'replays'}, {'label': 'Replays & Highlights', 'title':'Replays & Highlights'}, img=icon_path('sport_on_demand.jpg'), fanart=fanart, is_folder=True)
	addon.add_item({'mode': 'tools'}, {'label': 'Tools', 'title':'Tools'}, img=icon_path('tools.jpg'), fanart=fanart,is_folder=True)
	
	addon.end_of_directory()
	
#for debug purposes
elif mode[0]=='keyboard_open':

	
	keyboard = xbmc.Keyboard('', 'Enter URL:', False)
	keyboard.doModal()
	if keyboard.isConfirmed():
		query = keyboard.getText()
		if '.m3u8' in query:
			xbmc.Player().play(query)
		else:
			from resources.lib.modules import liveresolver
			resolved = liveresolver.Liveresolver().resolve(query)
			if resolved:
				if 'plugin://' in resolved['url']:
					xbmc.executebuiltin('RunPlugin({})'.format(resolved['url']))

				else:
					resolved = '{}|{}'.format(resolved['url'], urlencode(resolved['headers']))
					xbmc.Player().play(resolved)

elif mode[0] == 'open_category':
	category = args['category'][0]
	sources = os.listdir(AddonPath + '/resources/lib/sources/{}'.format(category))
	for source in sources:
		if '.pyo' not in source and '__init__' not in source and '__pycache__' not in source:
			try:
				source = source.replace('.py','')
				exec("from resources.lib.sources.{} import {}".format(category, source))
				info = eval(source+".info()")
				if info.enabled:
					addon.add_item({'mode': 'open_site', 'category': category, 'site': info.mode}, {'label': info.name, 'title': info.name}, img=icon_path(info.icon), fanart=fanart,is_folder=True)
			except Exception as e:
				log(str(e))
				pass
	if category in ['live_sport', 'live_tv']:
		addon.add_item({'mode': 'search', 'category': category}, {'label': 'Search', 'title': 'Search'}, img=icon_path('search.png'), fanart=fanart,is_folder=False)

	addon.end_of_directory()

elif mode[0] == 'search':
	category = args['category'][0]

	keyboard = xbmc.Keyboard('', 'Enter search query:', False)
	keyboard.doModal()
	if keyboard.isConfirmed():
		
		query = keyboard.getText()
		xbmc.executebuiltin("Container.Update(%s)"%addon.build_plugin_url({'mode': 'open_search', 'query':query, 'category': category}))

elif mode[0]=='open_search':
	category = args['category'][0]
	query = args['query'][0]

	sources = os.listdir(AddonPath + '/resources/lib/sources/{}'.format(category))
	for source in sources:
		if '.pyo' not in source and '__init__' not in source and '__pycache__' not in source and '.pyc' not in source:
			try:
				site = source.replace('.py','')
				exec("from resources.lib.sources.{} import {}".format(category, site))
				info = eval(site+".info()")
				srch = False
				try: srch = info.searchable
				except: pass
				if srch:
					s = eval(site+".main()")
					events = s.search(query)
					for event in events:
						try:
							img = icon_path(event[2])
						except:
							img = icon_path(info.icon)
						if not info.multilink:
							addon.add_item({'mode': 'play', 'category': category, 'url': event[0],'title':event[1], 'img': img,'site':site}, {'label': event[1], 'title': event[1].rstrip('[/B]')}, img=img, fanart=fanart, is_folder=False)
						else:
							if (control.setting('link_precheck') == 'false'):
								ctxt = [('Rescrape links', 'RunPlugin(%s)'%addon.build_plugin_url({'mode': 'get_links_refresh', 'url': event[0], 'category': category, 'site':site , 'title':event[1], 'img': img, 'timeout': 'true'}))]
							else:
								ctxt = []
							addon.add_item({'mode': 'get_links', 'url': event[0], 'category': category, 'site':site , 'title':event[1], 'img': img}, {'label': event[1],'title': event[1]}, img=img, fanart=fanart,  is_folder=True)
			except Exception as e:
				log("Error {} - {} - {}".format(category, site, e))
				pass

	addon.end_of_directory()


	

elif mode[0] == 'open_site':
	category = args['category'][0]
	site = args['site'][0]
	try:
		next_page = args['next'][0]
	except:
		next_page = None

	exec("from resources.lib.sources.{} import {}".format(category, site))
	info = eval(site+".info()")
	if not info.categorized:
		if next_page:
			source = eval(site+".main(url=next_page)")
		else:
			source = eval(site+".main()")
		try:
			events = source.events()
		except Exception as e:
			log(e)
			events = []
		for event in events:
			try:
				img = icon_path(event[2])
			except:
				img = icon_path(info.icon)

			if not info.multilink:

				addon.add_item({'mode': 'play', 'url': event[0], 'category': category, 'title':event[1], 'img': img,'site':site}, {'label': event[1], 'title':event[1].rstrip('[/B]')}, img=img, fanart=fanart, is_folder=False)
			else:
				if (control.setting('link_precheck') == 'false'):
					ctxt = [('Rescrape links', 'RunPlugin(%s)'%addon.build_plugin_url({'mode': 'get_links_refresh', 'url': event[0], 'category': category, 'site':site , 'title':event[1], 'img': img, 'timeout': 'true'}))]
				else:
					ctxt = []
				addon.add_item({'mode': 'get_links','site':site, 'category': category, 'url': event[0], 'title':event[1], 'img': img}, {'label': event[1], 'title': event[1]}, img=img, fanart=fanart,is_folder=True)
		if (info.paginated and source.next_page()):
			addon.add_item({'mode': 'open_site', 'site': info.mode, 'category': category, 'next' : source.next_page()}, {'label':'Next Page >>' ,'title': 'Next Page >>'}, img=icon_path(info.icon),  fanart=fanart,is_folder=True)

	else:
		source = eval(site+".main()")
		categories  = source.categories()
		
		for cat in categories:
			try:
				img = icon_path(cat[2])
			except:
				img = icon_path(info.icon)
			addon.add_item({'mode': 'open_site_category', 'url': cat[0], 'category': category, 'site': info.mode}, {'label': cat[1],'title': cat[1]}, img=img, fanart=fanart,is_folder=True)

	addon.end_of_directory()


elif mode[0]=='open_site_category':
	url = args['url'][0]
	site = args['site'][0]
	category = args['category'][0]
	exec("from resources.lib.sources.{} import {}".format(category, site))
	info = eval(site+".info()")
	source = eval(site+".main(url='{}')".format(url))
	try:
		events = source.events(url)
	except Exception as e:
		log(e)
		events = []

	for event in events:
		try:
			img = event[2]

		except:
			img = icon_path(info.icon)

		if not info.multilink:
			addon.add_item({'mode': 'play', 'category': category, 'url': event[0],'title':event[1], 'img': img,'site':site}, {'label': event[1], 'title':event[1].rstrip('[/B]')}, img=img, fanart=fanart, is_folder=False)
		else:
			if (control.setting('link_precheck') == 'false'):
				ctxt = [('Rescrape links', 'RunPlugin(%s)'%addon.build_plugin_url({'mode': 'get_links_refresh', 'url': event[0], 'category': category, 'site':site , 'title':event[1], 'img': img, 'timeout': 'true'}))]
			else:
				ctxt = []
			addon.add_item({'mode': 'get_links', 'url': event[0], 'category': category, 'site':site , 'title':event[1], 'img': img}, {'label':event[1] ,'title': event[1]}, img=img, fanart=fanart,contextmenu_items=ctxt, is_folder=True)
	
	if (info.paginated and source.next_page()):
		addon.add_item({'mode': 'open_site_category', 'category': category, 'site': info.mode, 'url': source.next_page()}, {'label': 'Next Page >>' ,'title': 'Next Page >>'}, img=icon_path(info.icon), fanart=fanart,is_folder=True)
	
	addon.end_of_directory()

elif mode[0] == 'refresh_links':
	url = args['url'][0]
	site = args['site'][0]
	category = args['category'][0]
	
	exec("from resources.lib.sources.{} import {}".format(category, site))
	info = eval(site+".info()")
	source = eval(site+".main()")
	try:
		cache.remove(source._links, url)
	except:
		pass
	xbmc.executebuiltin("Container.Refresh()")

elif mode[0]=='get_links':
	
	url = args['url'][0]
	title = args['title'][0]
	site = args['site'][0]
	category = args['category'][0]
	img = args['img'][0]
	
	exec("from resources.lib.sources.{} import {}".format(category, site))
	info = eval(site+".info()")
	source = eval(site+".main()")
	try:
		events = source.links(url)
	except:
		events = []
	
	for event in events:
		if (control.setting('link_precheck') == 'false'):
				ctxt = [('Rescrape links','RunPlugin(%s)'%addon.build_plugin_url({'mode': 'refresh_links', 'url': url, 'category': category, 'site':site}))]
		else:
			ctxt = []
		addon.add_item({'mode': 'play', 'url': event[0],'title':title, 'img': img, 'category': category, 'site':site}, {'label': event[1], 'title':title.rstrip('[/B]')}, img=img, fanart=fanart,contextmenu_items=ctxt, is_folder=False)
	if len(events) == 0:
		try: 
			a = hasattr(site, _links)
			addon.add_item({'mode': 'refresh_links', 'url': url, 'category': category, 'site':site}, {'label': 'Rescrape links', 'title': 'Rescrape links', 'img':img})
		except:
			pass
	addon.end_of_directory()
	

elif mode[0] == 'play':
	url = args['url'][0]
	title = args['title'][0]
	category = args['category'][0]
	img = args['img'][0]
	site = args['site'][0]

	exec("from resources.lib.sources.{} import {}".format(category, site))
	source = eval(site+'.main()')
	enc = False
	try:
		resolved, enc = source.resolve(url)
	except:
		resolved = source.resolve(url)
	if resolved:
		if 'plugin://' in resolved:
			xbmc.executebuiltin('RunPlugin({})'.format(resolved))
		else:
			li = xbmcgui.ListItem(title, path=resolved)
			li.setArt({'thumb': img})
			li.setInfo(type = 'Video', infoLabels={'Title': title.rstrip('[/B]'), 'mediatype': 'video'})
			li.setProperty('IsPlayable', 'true')
			if enc:
				KODI_VERSION_MAJOR = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
				if KODI_VERSION_MAJOR >= 19:
					li.setProperty('inputstream', 'inputstream.adaptive')
				else:
					li.setProperty('inputstreamaddon', 'inputstream.adaptive')

				li.setProperty('inputstream.adaptive.manifest_type', 'hls')
			xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)



########################################################################################################################################################################################################
########################################################################################################################################################################################################
########################################################################################################################################################################################################
####
####______________________________________________________________________________________________TOOLS_________________________________________________________________________________________________
####
########################################################################################################################################################################################################
########################################################################################################################################################################################################
########################################################################################################################################################################################################




elif mode[0]=='tools':
	addon.add_item({'mode': 'settings'}, {'label':'Settings', 'title':'Settings'}, img=icon_path('tools.jpg'), fanart=fanart,is_folder=True)
	addon.add_item({'mode': 'set_tz'}, {'label': 'Set Timezone: [B]{}[/B]'.format(constants.get_zone(int(control.setting('timezone_new'))))}, img=icon_path('tools.jpg'), fanart=fanart,is_folder=True)
	addon.add_item({'mode': 'keyboard_open'}, {'label':'Open URL', 'title':'Open URL'}, img=icon_path('tools.jpg'), fanart=fanart,is_folder=True)
	addon.add_item({'mode': 'clear_cache'}, {'label':'Clear addon cache', 'title':'Clear addon cache'}, img=icon_path('tools.jpg'), fanart=fanart,is_folder=True)

	addon.end_of_directory()

elif mode[0]=='clear_cache':
	from resources.lib.modules import cache
	cache.clear()

elif mode[0]=='settings':
	from resources.lib.modules import control
	control.openSettings()

elif mode[0]=='set_tz':
	cs = ['[B]Automatically set timezone[/B]']
	cs += constants.get_zone_categories()
	dialog = xbmcgui.Dialog()
	index = dialog.select("Select zone", cs)
	if index != -1:
		if index == 0:
			xbmc.executebuiltin('RunPlugin(%s)'%addon.build_plugin_url({'mode': 'auto_set_tz'}))
		else:
			zs = constants.get_zones_by_cat(cs[index])
			index = dialog.select("Select zone", zs)
			if index != -1:
				control.set_setting('timezone_new', str(constants.get_zone_idx(zs[index])))
				control.infoDialog('Timezone set: ' + str(zs[index]))
				control.refresh()

elif mode[0]=='auto_set_tz':
	from tzlocal import get_localzone # $ pip install tzlocal
	local_tz = get_localzone()
	control.set_setting('timezone_new', str(constants.get_zone_idx(local_tz.zone)))
	control.infoDialog('Timezone set: ' + local_tz.zone)
	control.refresh()



##################################################################################################################################
##################################################################################################################################

elif mode[0]=='reddit':
	from resources.lib.modules import subreddits
	items = subreddits.get_subreddits()
	for item in items:

		delete = addon.build_plugin_url({'mode':'delete_subreddit','reddit':item})
		context = [('Remove subreddit','Container.Update(%s)'%delete)]
		addon.add_item({'mode': 'open_subreddit', 'reddit': item}, {'title': item}, img=icon_path('reddit.jpg'), fanart=fanart,contextmenu_items=context,is_folder=True)

	addon.add_item({'mode': 'add_subreddit'}, {'title': '[B][COLOR green]Add a subreddit[/COLOR][/B]'}, img=icon_path('reddit.jpg'), fanart=fanart)    
	addon.end_of_directory()
elif mode[0]=='add_subreddit':
	from resources.lib.modules import subreddits
	subreddits.add_subreddit()
	control.refresh()

elif mode[0]=='delete_subreddit':
	reddit = args['reddit'][0]
	from resources.lib.modules import subreddits
	subreddits.remove_subreddit(reddit)
	control.refresh()

elif mode[0]=='open_subreddit':
	reddit = args['reddit'][0]
	from resources.lib.modules import subreddits
	items = subreddits.events(reddit)
	for item in items:
		addon.add_item({'mode': 'open_subreddit_event', 'url': item[0]}, {'title': item[1]}, img=icon_path('reddit.jpg'), fanart=fanart,is_folder=True)
	addon.end_of_directory()

elif mode[0]=='open_subreddit_event':
	url = args['url'][0]
	from resources.lib.modules import subreddits
	items = subreddits.event_links(url)
	for event in items:
		browser = 'plugin://plugin.program.chrome.launcher/?url=%s&mode=showSite&stopPlayback=no'%(event[0])


		context = [('Open in browser','Container.Update(%s)'%browser)]

		addon.add_video_item({'mode': 'play', 'url': event[0],'title':event[1], 'img': icon_path('reddit.jpg')}, {'title': event[1]}, img=icon_path('reddit.jpg'), fanart=fanart, contextmenu_items=context)
	addon.end_of_directory()

