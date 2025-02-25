from resources.lib.modules.log_utils import log
from resources.lib.modules import control, constants
import requests
import json
import time
import re
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode

class info():
	def __init__(self):
		self.mode = 'ustvgo'
		self.name = 'ustvgo'
		self.icon = 'ustvgo.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = False
		self.categorized = False
		self.multilink = False
		self.searchable = True


class main():
	
	def __init__(self, url = ''):
		self.base = 'https://ustvgo.tv'
		self.url = url

	def events(self):
		html = requests.get(self.base).text
		cs = re.findall('li>.+?href\s*=\s*[\"\']([^\"\']+).+?>([^<]+)', html)
		channels = []
		for c in cs:
			channels.append((c[0], c[1].strip()))
		return channels

	def resolve(self,url):
		#url = 'https://ustvgo.tv/{}'.format(url)
		html = requests.get(url, headers={'user-agent': constants.USER_AGENT}).text
		fid = re.findall('/clappr\.php\?stream=([^\"\']+)', html)
		if len(fid) == 0:
			return ' '
		fid = fid[0]
		post_url = 'https://ustvgo.tv/data.php'
		data = {'stream': fid}
		play_url = requests.post(post_url, data=data, headers={'origin':'https://ustvgo.tv', 'referer':'https://ustvgo.tv/clappr.php?stream={}'.format(fid), 'x-requested-with': 'XMLHttpRequest'}).text
		head = {'referer': 'https://ustvgo.tv/clappr.php?stream={}', 'user-agent': constants.USER_AGENT}
		return '{}|{}'.format(play_url, urlencode(head)), False

	def search(self, query):
		chs = self.events()

		evs = []
		for c in chs:
			if query.lower() in c[1].lower():
				evs.append(c)

		return evs