import re
import requests
import json
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
		return bool(re.search('castmax.+?\.js', self.s.get(url).text))

	def resolve(self, url, html = '', referer=None):
		try:
			#r = self.s.get(url).text
			r = html
			id = re.findall('id\s*=\s*[\"\']([^\"\']+).+?castmax.+?\.js', r)[0]
			width = '100%'
			height = '100%'
			jsurl = re.findall('src\s*=\s*[\"\'](.+?castmax.+?\.js)', html)[0]

			if urlparse(jsurl).scheme == '':
				jsurl = jsurl.replace('://', '')
				jsurl = 'http://' + jsurl
				jsurl = jsurl.replace('////','//')
			self.s.headers.update({'referer':url})
			htm = self.s.get(jsurl).text
			#find and build iframe
			ifr = re.findall('document\.write\s*\(([\"\']<\s*iframe[^\)]+)', htm)[0]
			ifr = eval(ifr)

			#get link from iframe
			uri = re.findall('i?frame\s*.+?src=[\"\']?([^\"\'\s]+)', ifr)[0]
			if urlparse(uri).scheme == '':
				uri = uri.replace('://', '')
				uri = 'http://' + uri
				uri = uri.replace('////','//')
			
			html = self.s.get(uri)

			return None
		except Exception as e:
			log('Castmax error: ' + str(e))
			return None