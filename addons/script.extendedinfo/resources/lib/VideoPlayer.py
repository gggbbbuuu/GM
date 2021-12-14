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
		Utils.hide_busy()
		xbmc.sleep(50)
		while xbmc.Player().isPlaying():
			while xbmc.getCondVisibility('Window.IsActive(10138)'):
				xbmc.sleep(50)
		xbmc.sleep(250)
		#self.stopped = False

	def container_position(self, container=None, position=None):
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
		return result

	def play_youtube_direct(self, url):
		from resources.lib import library
		import sys
		#params['path'] = 'play'
		#params['video_id'] = '7hdgx-W2VMQ'
		parentdir = library.main_file_path().replace(library.addon_ID(),'plugin.video.youtube')
		sys.argv = ['plugin://plugin.video.youtube/play/', '-1', '?video_id=' + str(self.youtube_id), 'resume:false']

		sys.path.insert(0,parentdir) 

		import default
		del default
		return

	def play(self, url, listitem, window=False):
		"""
		import xbmcvfs
		container = xbmc.getInfoLabel('System.CurrentControlId')
		position = int(xbmc.getInfoLabel('Container('+str(container)+').CurrentItem'))-1
		if Utils.window_stack_enable == 'false':
			xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
			window2 = window
			gc.collect()
			try: 
				import os
				logpath = xbmcvfs.translatePath('special://logpath') + str('kodi.log')
				logpath_size = float(os.path.getsize(logpath))
			except:
				logpath_size = 0
			windows_flag = False
			try:
				import subprocess, signal
				f = subprocess.Popen(['tail','-F',logpath],stdout=subprocess.PIPE,stderr=subprocess.PIPE, preexec_fn=os.setsid)
			except: 
				windows_flag = True
			if windows_flag == True and int(logpath_size) < 100:
				super(VideoPlayer, self).play(item=url, listitem=listitem, windowed=False, startpos=-1)
			else:
				xbmc.executebuiltin('RunPlugin(%s)' % url)
			Utils.show_busy()
			toggle = False
			while 1==1:
				if windows_flag == True and int(logpath_size) < 100:
					xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
					for i in range(600):
						if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
							window.close()
							try:
								window = None
								del window
							except: 
								pass
							self.wait_for_video_end()
							window2.close()
							self.container_position(container=container,position=position)
							#return window2.doModal()
							window2.doModal()
							try: window2.close()
							except: pass
							try: del window2
							except: pass
							try: del self
							except: pass
							return
							break
						xbmc.sleep(50)
				if windows_flag == True and int(logpath_size) > 100:
					import collections
					line = collections.deque(open(logpath), 5)
				if windows_flag == False and int(logpath_size) > 100:
					line = f.stdout.readline()
				if 'VideoPlayer::OpenFile:' in str(line) and int(logpath_size) > 100:
					Utils.hide_busy()
					try: window.close()
					except: pass
					try:
						window = None
						del window
					except: 
						pass
					toggle = True
					xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
				if 'CVideoPlayer::CloseFile()' in str(line) and toggle and int(logpath_size) > 100:
					toggle = False
					break
			window2.close()
			if  windows_flag == False:
				os.killpg(os.getpgid(f.pid), signal.SIGTERM) 
			self.container_position(container=container,position=position)
			#return window2.doModal()
			window2.doModal()
			try: window2.close()
			except: pass
			try: del window2
			except: pass
			try: del self
			except: pass
			return
		"""
		from resources.lib.WindowManager import wm
		container = xbmc.getInfoLabel('System.CurrentControlId')
		position = int(xbmc.getInfoLabel('Container('+str(container)+').CurrentItem'))-1
		super(VideoPlayer, self).play(item=url, listitem=listitem, windowed=False, startpos=-1)
		for i in range(600):
			if xbmc.getCondVisibility('VideoPlayer.IsFullscreen'):
				if window and window.window_type == 'dialog':
					wm.add_to_stack(window)
					window.close()
					if Utils.window_stack_enable == 'true':
						window = None
						del window
					self.wait_for_video_end()
					if Utils.window_stack_enable == 'false':
						self.container_position(container=container,position=position)
						window.doModal()
						window = None
						del window
						return
					self.container_position(container=container,position=position)
					return wm.pop_stack()
			xbmc.sleep(50)

	def play_from_button1(self, url, listitem, window=False, type='', dbid=0):
		import collections
		import subprocess, signal, os
		import xbmcvfs
		container = xbmc.getInfoLabel('System.CurrentControlId')
		position = int(xbmc.getInfoLabel('Container('+str(container)+').CurrentItem'))-1
		if Utils.window_stack_enable == 'false':
			#super(VideoPlayer, self).play(item=url, listitem=listitem, windowed=False, startpos=-1)
			Utils.show_busy()
			xbmc.executebuiltin('RunPlugin(%s)' % url)
			xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
			window2 = window
			gc.collect()
			logpath = xbmcvfs.translatePath('special://logpath') + str('kodi.log')
			windows_flag = False
			try: f = subprocess.Popen(['tail','-F',logpath],stdout=subprocess.PIPE,stderr=subprocess.PIPE, preexec_fn=os.setsid)
			except: windows_flag = True
			while 1==1:
				if windows_flag == True:
					line = collections.deque(open(logpath), 5)
				else:
					line = f.stdout.readline()
				if 'VideoPlayer::OpenFile:' in str(line):
					Utils.hide_busy()
					try: window.close()
					except: pass
					try:
						window = None
						del window
					except: 
						pass
					xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
					#Utils.hide_busy()
					#Utils.hide_busy()
					#
				if 'CVideoPlayer::CloseFile()' in str(line):
					break
			window2.close()
			if  windows_flag == False:
				os.killpg(os.getpgid(f.pid), signal.SIGTERM) 
			self.container_position(container=container,position=position)
			#return window2.doModal()
			window2.doModal()
			try: window2.close()
			except: pass
			try: del window2
			except: pass
			try: del self
			except: pass
			return
		from resources.lib.WindowManager import wm
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
		#import subprocess, signal, os
		import collections
		import xbmcvfs
		container = xbmc.getInfoLabel('System.CurrentControlId')
		position = int(xbmc.getInfoLabel('Container('+str(container)+').CurrentItem'))-1
		if Utils.window_stack_enable == 'false':
			#super(VideoPlayer, self).play(item=url, listitem=listitem, windowed=False, startpos=-1)
			Utils.show_busy()
			xbmc.executebuiltin('RunPlugin(%s)' % url)
			xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
			window.close()
			xbmcgui.Window(10000).setProperty(str(addon_ID_short())+'_running', 'True')
			window2 = window
			window = None
			del window
			gc.collect()
			logpath = xbmcvfs.translatePath('special://logpath') + str('kodi.log')
			#f = subprocess.Popen(['tail','-F',logpath],stdout=subprocess.PIPE,stderr=subprocess.PIPE, preexec_fn=os.setsid)
			while True:
				#line = f.stdout.readline()
				line = collections.deque(open(logpath), 5)
				if 'VideoPlayer::OpenFile:' in str(line):
					Utils.hide_busy()
					xbmc.executebuiltin('ActivateWindow(FullScreenVideo)')
					Utils.hide_busy()
				if 'CVideoPlayer::CloseFile()' in str(line):
					break
			window2.close()
			#os.killpg(os.getpgid(f.pid), signal.SIGTERM) 
			self.container_position(container=container,position=position)
			window2.doModal()
			try: window2.close()
			except: pass
			try: del window2
			except: pass
			try: del self
			except: pass
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
		xbmcgui.Window(10000).setProperty('diamond_info_time', str(int(time.time())+120))
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