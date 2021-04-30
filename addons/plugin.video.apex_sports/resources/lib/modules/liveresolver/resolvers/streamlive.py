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

	def priority(self):
		return -1

	def isSupported(self, url, html):
		return bool(re.search('streamlive.to.+?channel', self.s.get(url).text))

	def resolve(self, url, html = '', referer=None):	
		try:

			headers = {'Host':'www.streamlive.to','Referer':referer,'Connection':'keep-alive'}
			self.s.headers.update(headers)
			result = self.s.get(url).text
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
			server = "https:" + "".join(eval(infos[0])).replace('\\/','/')
			
			var1 = v2[infos[1]]

			var2 = ids2[infos[2]]
			play_url = server + var1 + var2 
			return {'url': play_url, 'headers': {'referer': url}}
		except Exception as e:
			log(e)
			return None
		