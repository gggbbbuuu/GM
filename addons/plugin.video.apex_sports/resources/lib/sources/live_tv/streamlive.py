from resources.lib.modules import cache
from resources.lib.modules.log_utils import log
from resources.lib.modules import control
import requests
import re
import os
try:
	from urllib.parse import urlencode, quote_plus
except:
	from urllib import urlencode, quote_plus

class info():
	def __init__(self):
		self.mode = 'streamlive'
		self.name = 'Streamlive.to'
		self.icon = 'streamlive.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = False
		self.categorized = False
		self.multilink = False
		self.searchable = True


class main():
	
	def __init__(self, url = 'https://www.streamlive.to/channels/?sort=1'):
		self.base = 'https://www.streamlive.to/'
		self.url = url

	def events(self):
		events = []
		with open(os.path.join(control.addonPath,'resources/chs.txt'), 'r') as f:
			t = f.read().split('\n')
			for c in t:
				fid = c.split(' ')[-1].strip()
				name = c.replace(fid, '').strip()
				events.append((fid, name))

		events.sort(key=lambda x: x[1])
		return events


	def resolve(self,url):
		url = 'https://www.streamlive.to/channel-player?n={}'.format(url)
		from resources.lib.modules import liveresolver
		d = liveresolver.Liveresolver().resolve(url)
		if not d or d is None:
			return ' '
		if d['url'].startswith('plugin://'):
			return d['url']

		if d:
			return '{}|{}'.format(d['url'], urlencode(d['headers'])), False
		return ' '

	def search(self, query):
		evs = self.events()
		events = []
		for e in evs:
			if query.lower() in e[1].lower():
				events.append(e)
		return events