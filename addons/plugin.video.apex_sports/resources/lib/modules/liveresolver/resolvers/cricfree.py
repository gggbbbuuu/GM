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
		return bool(re.search('crichd.+?\.js', self.s.get(url).text))

	def resolve(self, url, html = '', referer=None):
		try:
			r = html
			fid = re.findall('id\s*=\s*[\"\']([^\"\']+).+?crichd.+?\.js', r)[0]
			v_width = '100%'
			v_height = '100%'
			jsurl = re.findall('src\s*=\s*[\"\'](.+?crichd.+?\.js)', html)[0]

			if urlparse(jsurl).scheme == '':
				jsurl = jsurl.replace('://', '')
				jsurl = 'http://' + jsurl
				jsurl = jsurl.replace('////','//')
			self.s.headers.update({'referer':url})
			htm = self.s.get(jsurl).text
			#find and build iframe
			ifr = re.findall('document\.write\s*\(([\"\']<\s*ifr[^\)]+)', htm)[0]
			ifr = eval(ifr)

			#get link from iframe
			uri = re.findall('i?frame\s*.+?src=[\"\']?([^\"\'\s]+)', ifr)[0]
			if urlparse(uri).scheme == '':
				uri = uri.replace('://', '')
				uri = 'http://' + uri
				uri = uri.replace('////','//')
			
			result = self.s.get(uri).text
			variables = re.findall("var\s*([^\s=]+)\s*=\s*(\[[^\]]+\])\s*;", result)
			v2 = {}
			for v in variables:
				v2[v[0]] = "".join(eval(v[1]))

			ids = re.findall('id\s*=\s*([^<]+)>([^<]+)', result)

			ids2 = {}
			for v in ids:
				ids2[v[0]] = v[1]
			try:
				infos = re.findall('(\[[^\]]+\]).join.+? \+\s*([a-zA-Z]+).join.+?\+.+?document.getElementById\([\"\']([^\"\']+)', result)[0]
			except Exception as e:
				return None
			server = "".join(eval(infos[0])).replace('\\/','/')
			
			var1 = v2[infos[1]]

			var2 = ids2[infos[2]]
			play_url = server + var1 + var2
			return {'url': play_url, 'headers': {'referer': uri, 'user-agent':USER_AGENT}}
		except Exception as e:
			log('Cricfree error: ' + str(e))
			return None