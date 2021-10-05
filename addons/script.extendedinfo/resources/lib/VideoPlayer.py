import xbmc, xbmcgui
from resources.lib import Utils
import gc
from resources.lib.library import addon_ID_short
import json

class VideoPlayer(xbmc.Player):

	"""
	def __init__(self, *args, **kwargs):
		#super(VideoPlayer, self).__init__()
		self.stopped = False

	def onPlayBackEnded(self):
		self.stopped = True

	def onPlayBackStopped(self):
		self.stopped = True

	def onPlayBackStarted(self):
		self.stopped = False

	def onAVStarted(self):
		self.stopped = False
	"""

	def wait_for_video_end(self):
		xbmc.sleep(50)
		while xbmc.Player().isPlaying():
			xbmc.sleep(500)
			while xbmc.getCondVisibility('Window.IsActive(10138)'):
				xbmc.sleep(50)
		xbmc.sleep(250)
		#self.stopped = False

	def play(self, url, listitem, window=False):
		from resources.lib.WindowManager import wm
		container = xbmc.getInfoLabel('System.CurrentControlId')
		position = xbmc.getInfoLabel('Container('+str(container)+').Position')
		#import time
		#xbmcgui.Window(10000).setProperty('diamond_info_time', str(int(time.time())+20))
		if Utils.window_stack_enable == 'false':
			#super(VideoPlayer, self).play(item=url, listitem=listitem, windowed=False, startpos=-1)
			Utils.show_busy()
			xbmc.executebuiltin('RunPlugin(%s)' % url)
			#xbmcgui.Window(10000).clearProperty('diamond_info_time')
			xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
			window.close()
			xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
			window2 = window
			window = None
			del window
			gc.collect()
			for i in range(600):
				if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
					Utils.hide_busy()
					self.wait_for_video_end()
					#try: wm.open_dialog(window2, None)
					#except: wm.pop_stack2(window2)

					params = {'sender': addon_ID_short(),
									  'message': 'SetFocus',
									  'data': {'command': 'SetFocus',
												   'command_params': {'container': container, 'position': position}
												   },
									  }

					command = json.dumps({'jsonrpc': '2.0',
												  'method': 'JSONRPC.NotifyAll',
												  'params': params,
												  'id': 1,
												  })
					result = xbmc.executeJSONRPC(command)
					wm.pop_stack2(window2)
					window2 = None
					del window2
					#xbmc.log(str(container)+'===>PHIL', level=xbmc.LOGINFO)
					#xbmc.log(str(position)+'===>PHIL', level=xbmc.LOGINFO)
					#xbmc.executebuiltin('SetFocus('+str(container)+','+str(position)+')')
					return 
				xbmc.sleep(50)
			#xbmc.executebuiltin('ActivateWindow(FullScreenVideo)')

		#	window.close()
		#	gc.collect()
		#	#xbmc.executebuiltin('RunPlugin(%s)' % url)
		#	del window
		#	#xbmc.executebuiltin('Dialog.Close(all,true)')
		#	#try: self.close()
		#	#except: pass
		#	return
		super(VideoPlayer, self).play(item=url, listitem=listitem, windowed=False, startpos=-1)
		for i in range(600):
			if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
				if window and window.window_type == 'dialog':
					wm.add_to_stack(window)
					window.close()
					window = None
					del window
					self.wait_for_video_end()
					return wm.pop_stack()
			xbmc.sleep(50)

	def play_from_button2(self, url, listitem, window=False, type='', dbid=0):
		from resources.lib.WindowManager import wm
		#for k,v in sys.modules.items():
		#	if k.startswith('xbmc'):
		#		importlib.reload(v)
		#import xbmc, xbmcgui, xbmcaddon
		container = xbmc.getInfoLabel('System.CurrentControlId')
		position = xbmc.getInfoLabel('Container('+str(container)+').Position')
		#import time
		#xbmcgui.Window(10000).setProperty('diamond_info_time', str(int(time.time())+20))
		if dbid != 0:
			item = '{"%s": %s}' % (type, dbid)
		else:
			item = '{"file": "%s"}' % url
		if Utils.window_stack_enable == 'false':
			Utils.show_busy()
			#super(VideoPlayer, self).play(item=url, listitem=listitem, windowed=False, startpos=-1)
			xbmc.executebuiltin('RunPlugin(%s)' % url)
			#xbmcgui.Window(10000).clearProperty('diamond_info_time')
			xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
			window2 = window
			wm.close_stack(window)
			window = None
			del window
			gc.collect()
			xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
			for i in range(600):
				if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
					Utils.hide_busy()
					self.wait_for_video_end()
					params = {'sender': addon_ID_short(),
									  'message': 'SetFocus',
									  'data': {'command': 'SetFocus',
												   'command_params': {'container': container, 'position': position}
												   },
									  }

					command = json.dumps({'jsonrpc': '2.0',
												  'method': 'JSONRPC.NotifyAll',
												  'params': params,
												  'id': 1,
												  })
					result = xbmc.executeJSONRPC(command)
					wm.pop_stack2(window2)
					window2 = None
					del window2
					#xbmc.log(str(container)+'===>PHIL', level=xbmc.LOGINFO)
					#xbmc.log(str(position)+'===>PHIL', level=xbmc.LOGINFO)
					#xbmc.executebuiltin('SetFocus('+str(container)+','+str(position)+')')
					return 
				xbmc.sleep(50)
			#xbmc.executebuiltin('RunPlugin(%s)' % url)
#			del window
			#xbmc.executebuiltin('Dialog.Close(all,true)')
			#try: self.close()
			#except: pass
			return
		Utils.get_kodi_json(method='Player.Open', params='{"item": %s}' % item)
		for i in range(600):
			if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
				if window and window.window_type == 'dialog':
					wm.add_to_stack(window)
					window.close()
					window = None
					del window
					self.wait_for_video_end()
					return wm.pop_stack()
			xbmc.sleep(50)


	def play_from_button(self, url, listitem, window=False, type='', dbid=0):
		from resources.lib.WindowManager import wm
		import time
		xbmcgui.Window(10000).setProperty('diamond_info_time', str(int(time.time())+20))
		if dbid != 0:
			item = '{"%s": %s}' % (type, dbid)
		else:
			item = '{"file": "%s"}' % url
		if Utils.window_stack_enable == 'false':
			super(VideoPlayer, self).play(item=url, listitem=listitem, windowed=False, startpos=-1)
			window.close()
			gc.collect()
			#xbmc.executebuiltin('RunPlugin(%s)' % url)
			del window
			#xbmc.executebuiltin('Dialog.Close(all,true)')
			#try: self.close()
			#except: pass
			return
		Utils.get_kodi_json(method='Player.Open', params='{"item": %s}' % item)
		for i in range(600):
			if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
				if window and window.window_type == 'dialog':
					wm.add_to_stack(window)
					window.close()
					window = None
					del window
					self.wait_for_video_end()
					return wm.pop_stack()
			xbmc.sleep(50)

	def playtube(self, youtube_id=False, listitem=None, window=False):
		url = 'plugin://plugin.video.youtube/play/?video_id=%s' % str(youtube_id)
		self.play(url=url, listitem=listitem, window=window)

PLAYER = VideoPlayer()