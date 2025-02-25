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
		return bool(re.search('channel\s*=.+?playerfs.+?js', html))

	def resolve(self, url, html = '', referer=None):
		try:
			channel, g = re.findall('channel\s*=\s*[\"\']([^\"\']+).+?g\s*=\s*[\"\']([^\"\']+)', html)[0]
			jsur = re.findall('src\s*=\s*[\"\'](.+?playerfs.+?\.js)', html)[0]
			jsur = jsur + '?channel=' + channel
			width = '900'
			height = '480'
			self.s.headers.update({'referer':url})

			#load js file
			js = self.s.get(jsur).text

			#find some variables
			fid = re.findall('fid\s*=\s*[\"\']([^\"\']+)', js)[0]
			embedded = re.findall('embedded\s*=\s*[\"\']([^\"\']+)', js)[0]

			#find and build iframe
			ifr = re.findall('document\.write\s*\(([\"\']<\s*iframe[^\)]+)', js)[0]
			ifr = eval(ifr)

			#get link from iframe
			uri = re.findall('i?frame\s*.+?src=[\"\']?([^\"\'\s]+)', ifr)[0]

			self.s.headers.update({'referer':url})
			html = self.s.get(uri).text
			
			loadbalancer = re.findall('[\"\'](.+?loadbalancer[^\"\']+)[\"\'].+?(\d+)', html)[0]
			loadbalancer = loadbalancer[0] + loadbalancer[1]
			h2 = self.s.get(loadbalancer).text
			ea = h2.split('=')[1]

			hlsUrl = eval(re.findall('hlsurl\s*=\s*([^\n]+)', html, re.IGNORECASE)[0])
			id = re.findall('hlsurl\s*\+\s*.+?\(\s*[\"\']([^\"\']+)', html, re.IGNORECASE)[0]
			play_url = hlsUrl + id
			return {'url': play_url, 'headers':{'referer':url, 'user-agent':USER_AGENT}}
		except Exception as e:
			log(e)
			return None