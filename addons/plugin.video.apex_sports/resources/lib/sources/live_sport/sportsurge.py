from resources.lib.modules import cache, linkSearch, constants, control
from resources.lib.modules.log_utils import log
import json
from datetime import date, datetime
import requests
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode

class info():
	def __init__(self):
		self.mode = 'sportsurge'
		self.name = 'Sportsurge'
		self.icon = 'sportsurge.jpg'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = False
		self.categorized = True
		self.multilink = True

class main():
	def __init__(self, url = ''):
		self.base = 'https://sportsurge.net/'
		self.session = requests.session()
		self.session.headers.update({'user-agent': constants.USER_AGENT})

	def categories(self):
		out = []
		
		self.session.headers.update({'referer': self.base})
		url = 'https://api.sportsurge.net/groups/list?parent=0'
		html = self.session.get(url).text
		cats = json.loads(html)['groups']

		out = []
		for l in cats:
			id = l['id']
			logo = l['imageurl'] if 'http' in l['imageurl'] else (self.base + l['imageurl'])
			title = l['name']
			out.append((id, title, logo))

		return out

	def events(self, id):
		out = []
		ids = [id]
		
		sub_url = 'https://api.sportsurge.net/groups/list?parent={}'.format(id)
		self.session.headers.update({'referer': self.base})
		subs = json.loads(self.session.get(sub_url).text)['groups']
		for sub in subs:
			ids.append(sub['id'])
		for id in ids:
			url = 'https://api.sportsurge.net/events/list?group={}'.format(id)
			self.session.headers.update({'referer': self.base})
			html = self.session.get(url).text
			events = json.loads(html)['events']
			out = []
			for e in events:
				id = e['id']
				title = u'{} - {}'.format(e['name'], e['description'])
				out.append((id, title))
		
		return out

	#timeout in minutes
	def links(self, url, timeout=10):
		return cache.get(self._links, timeout, url)

	def _links(self, id):
		out = []
		out2 = []
		counter = 0
		
		uri = 'https://api.sportsurge.net/streams/list?event={}'.format(id)
		self.session.headers.update({'referer': self.base})
		html = requests.get(uri).text
		
		links = json.loads(html)['streams']

		titles = {}
		for r in links:
			title = u'{} {}@{} ({})'.format(r['coverage'], r['resolution'], r['framerate'], r['language'])
			url = r['url']
			titles[url] = title

			out.append((url, title))
		

		links = [u[0] for u in out]

		ret = linkSearch.getLinks(links)

		
		out2 = []
		for u in ret:
			out2.append((u, titles[u]))

		return out2
	
	

	def resolve(self,url):
		from resources.lib.modules import liveresolver
		d = liveresolver.Liveresolver().resolve(url)
		if not d:
			return None
		if d['url'].startswith('plugin://'):
			return d['url']
		if d:
			return '{}|{}'.format(d['url'], urlencode(d['headers'])), False
		return ' '