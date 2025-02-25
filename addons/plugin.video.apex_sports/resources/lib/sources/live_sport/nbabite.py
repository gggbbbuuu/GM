# -*- coding: UTF-8 -*-
from resources.lib.modules import  webutils, control, cache, linkSearch, constants
from resources.lib.modules.log_utils import log
import re
import requests
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode


class info():
	def __init__(self):
		self.mode = 'nbabite'
		self.name = 'NBAStreams'
		self.icon = 'nba.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = False
		self.categorized = False
		self.multilink = True

class main():
	def __init__(self, url = ''):
		
		self.base = 'https://nbabite.com'

	
	def events(self):
		out = []
		
		
		
		html = requests.get(self.base).text
		leagues = webutils.bs(html).findAll('div', {'class':'competition'})


		out = []

		for l in leagues:
			name = l.find('div', {'class':'info'}).getText().strip()
			league_name = u'[COLOR blue]► {}[/COLOR]'.format(name)
			out.append(('x', league_name))
			events = l.findAll('div', {'class':'col-md-6 col-sm-6'})
			for e in events:
				url = e.find('a')['href']
				names = re.sub('-live-stream[^\/$]*\/?', '', url)
				names = names.split('/')[-1].split('vs')
				divs = e.find('div', {'class':'match'}).findAll('div', {'class':'team-name'})
				live = e.find('div', {'class':'status live-indicator'})
				homeName = names[0].replace('-',' ').title()
				awayName = names[1].replace('-',' ').title()
				if live:
					scores = e.findAll('div', {'class':'score'})
					home = scores[0].getText()
					away = scores[1].getText()
					title = u'([COLOR red]LIVE[/COLOR]) {} [B]{}[/B] - [B]{}[/B] {} | {}'.format(homeName, home, away, awayName, live.getText())
				else:
					time = e.find('div', {'class':'status'}).getText()
					try: time = self.convert_time(time)
					except: time = None
					if time is None:
						continue
					title = u'({}) [B]{} - {}[/B]'.format(time, homeName, awayName)
				out.append((url,title))
		return out

	def links(self, url, timeout=int(control.setting('cache_timeout'))):
		return self._links(url)

	def _links(self, url):
		out = []
		out2 = []
		html = requests.get(url, headers={'Referer':self.base}).text
		id = re.findall('streamsmatchid\s*=\s*(\d+)\;',  html, flags=re.I)[0]

		uri = 'https://sportscentral.io/streams-table/{}/basketball?new-ui=1&origin=nbabite.com'.format(id)
		html = requests.get(uri, headers={'user-agent': constants.USER_AGENT, 'referer':url}).text
		soup = webutils.bs(html).find('table', {'class':'table streams-table-new'})

		try:
			rows = soup.findAll('tr')
		except:
			return []
		rows.pop(0)
		titles = {}
		for r in rows:
			h = r.findAll('td')
			title = '{} {} ({})'.format(h[7].getText().strip(), h[4].getText().strip(), h[5].getText().strip())
			url = r['data-stream-link']
			titles[url] = title

			out.append((url, title))

		links = [u[0] for u in out]
		ret = linkSearch.getLinks(links)
		out2 = []
		for u in ret:
			out2.append((u, titles[u]))

		return out2
	
	@staticmethod
	def convert_time(time):
		li = time.split(':')
		hour,minute=li[0],li[1]
		import datetime
		import pytz
		d = pytz.timezone(str(pytz.timezone('US/Eastern'))).localize(datetime.datetime(2000 , 1, 1, hour=int(hour), minute=int(minute)))
		timezona = control.setting('timezone_new')
		my_location = pytz.timezone(constants.get_zone(int(timezona)))
		convertido=d.astimezone(my_location)
		fmt = "%H:%M"
		time=convertido.strftime(fmt)
		return time

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