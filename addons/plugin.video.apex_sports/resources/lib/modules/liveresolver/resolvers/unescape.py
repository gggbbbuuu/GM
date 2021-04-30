import re
import requests
import base64
from resources.lib.modules.log_utils import log
from resources.lib.modules.constants import USER_AGENT

try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2


class Resolver():

	def __init__(self):
		self.hosts = {}
		self.headers = {'User-Agent': USER_AGENT, 'Cache-control': 'no-cache'}
		self.s = requests.session()
		self.s.headers.update(self.headers)

	def isSupported(self, url, html):
		return bool(re.search('unescape\([\"\']', html))

	def resolve(self, url, html='', referer=None):
		#try:
			#r = self.s.get(url).text
			r = html

			s = re.findall('unescape\([\"\']([^\"\']+)', r)
			for x in s:
				x = x.replace('@', '%')
				import urllib
				html = urllib.unquote(x).decode('utf8')
				try:
					play_url = re.findall('[\"\']((?:http)?[^\"\'\s]+m3u8[^\"\']*)[\"\']', html, re.M)[0]
					if play_url == '.m3u8':
						return {}
					if urlparse(play_url).scheme == '':
						play_url = play_url.replace('://', '').replace('//', '')
						play_url = 'http://' + play_url

					if '||' in play_url:
						return {}
					return {'url': play_url, 'headers': {'Referer': url, 'User-Agent':USER_AGENT, 'Host': urlparse(play_url).netloc}}
				except:
					continue

			return None
		#except:
	#		return None

