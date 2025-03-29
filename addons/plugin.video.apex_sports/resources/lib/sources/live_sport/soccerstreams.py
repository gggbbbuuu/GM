from resources.lib.modules import webutils, control, cache, linkSearch
from resources.lib.modules.log_utils import log
import re, json
from datetime import date, datetime
import requests
from resources.lib.modules.constants import USER_AGENT
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode

class info():
	def __init__(self):
		self.mode = 'soccerstreams'
		self.name = 'SoccerStreams'
		self.icon = 'soccer.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = False
		self.categorized = True
		self.multilink = True

class main():
	def __init__(self, url = ''):
		t1 = datetime.now()
		t2 = datetime.utcnow()
		delay = str(-1*int(round((t1-t2).total_seconds()/60)))
		today = date.today()
		dt = today.strftime("%Y-%m-%d")
		self.base = 'https://sportscentral.io/new-api/matches?timeZone={}&date={}'.format(delay, dt)
		self.ref = 'reedditt.soccerstreams.net'

	def categories(self):
		out = []
		
		def get(url):
			s = requests.session()
			s.headers.update({'Referer': 'https://reedditt.soccerstreams.net/home', 'user-agent':USER_AGENT, 'accept':'application/json'})
			return s.get(url).text
		
		html = cache.get(get, 10*60, self.base)
		leagues = json.loads(html)

		out = []
		for l in leagues:
			id = l['id']
			logo = l['logo']
			title = u'{} ({})'.format(l['name'], l['country']['name'])
			t = False
			if len(l['events']) > 0:
				for e in l['events']:
					if e['status']['type'] == 'finished':
						continue
					else:
						t = True
				if t:
					out.append((id, title, logo))

		return out
	def events(self, id):
		out = []
		
		def get(url):
			s = requests.session()
			s.headers.update({'Referer': 'https://reedditt.soccerstreams.net/home', 'user-agent':USER_AGENT, 'accept':'application/json'})
			return s.get(url).text
		
		html = cache.get(get, 5, self.base)
		events = json.loads(html)

		out = []
		for league in events:

			if str(league['id']) == str(id):
				logo = league['logo']
				lname = league['name']

				for e in league['events']:
					if e['status']['type'] == 'finished':
						continue
					live = e['status']['type'] == 'inprogress'
					time = e['startTimestamp']
					from dateutil import tz
					start = datetime.fromtimestamp(time, tz=tz.gettz(control.setting('timezone_new'))).strftime('%H:%M')
					title = u'({}) [B]{}[/B] - [B]{}[/B]'.format(start, e['homeTeam']['name'], e['awayTeam']['name'])
					if live:
						title = u'([COLOR red]{} - LIVE[/COLOR]) [B]{}[/B] - [B]{}[/B]'.format(start, e['homeTeam']['name'], e['awayTeam']['name'])
					out.append((e['id'],title.encode('utf-8'), logo))
				break
		
		return out

	#timeout in minutes
	def links(self, url, timeout=int(control.setting('cache_timeout'))):
		#return self._links(url)
		return cache.get(self._links, timeout, url)

	def _links(self, url):
		out = []
		out2 = []
		counter = 0
		#try:
		uri = 'https://streams.101placeonline.com/streams-table/{}/soccer?new-ui=1&origin={}'.format(url, self.ref)
		html = requests.get(uri).text
		soup = webutils.bs(html).find('table', {'class':'table streams-table-new'})

		try:
			rows = soup.findAll('tr')
		except:
			return []
		rows.pop(0)
		titles = {}
		for r in rows:
			h = r.findAll('td')
			title = u'{} {} ({})'.format(h[7].getText().strip(), h[4].getText().strip(), h[5].getText().strip())
			url = r['data-stream-link']
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
		if not d or d is None:
			return ' '
		if d['url'].startswith('plugin://'):
			return d['url']

		if d:
			return '{}|{}'.format(d['url'], urlencode(d['headers'])), False
		return ' '