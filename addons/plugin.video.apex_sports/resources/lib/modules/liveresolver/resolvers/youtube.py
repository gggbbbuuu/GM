import re
import requests
import json
from resources.lib.modules.constants import USER_AGENT

try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2
from resources.lib.modules.log_utils import log



'''
	Youtube finder and resolver.
	Finds video ID and passes it to youtube addon.
'''
class Resolver():

	def __init__(self):
		self.hosts = {}
		self.headers = {'User-Agent': USER_AGENT, 'Cache-control': 'no-cache'}
		self.s = requests.session()
		self.s.headers.update(self.headers)
		
	def priority(self):
		return 1000

	def isSupported(self, url, html):
		return bool(re.search('(?:youtube(?:-nocookie)?\.com\/(?!(?:live_chat))(?:[^\/\n\s]+\/\S*\/|(?:v|e(?:mbed)?)\/|\S*?[\?\&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})\W', html))

	def resolve(self, url, html = '', referer=None):
		
		yt_id = re.findall('(?:youtube(?:-nocookie)?\.com\/(?!(?:live_chat))(?:[^\/\n\s]+\/\S*\/|(?:v|e(?:mbed)?)\/|\S*?[\?\&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})\W', html)[0]
		url = 'plugin://plugin.video.youtube/play/?video_id={}'.format(yt_id)
		return {'url' : url, 'headers':{}}
		
		