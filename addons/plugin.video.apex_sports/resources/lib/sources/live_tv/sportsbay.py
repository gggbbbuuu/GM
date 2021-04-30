from resources.lib.modules import cache
from resources.lib.modules.log_utils import log
from resources.lib.modules import control, constants, webutils, cache
import requests
import re
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode

class info():
	def __init__(self):
		self.mode = 'sportsbay'
		self.name = 'Sportsbay.org'
		self.icon = 'sportsbay.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = True
		self.categorized = False
		self.multilink = True


class main():
	
	def __init__(self, url = 'https://sportsbay.org/sports/tv-channels/1'):
		self.base = 'https://sportsbay.org'
		self.url = url
		self.s = requests.session()
		self.headers = {'user-agent': constants.USER_AGENT, 'referer': self.base}
		self.s.headers.update(self.headers)

	def events(self):
		out = []
			
		html = self.s.get(self.url).text
		soup = webutils.bs(html)
		chs = soup.findAll('tr', {'class': 'vevent'})
		for c in chs:
			country = c.find('td', {'class': 'competition'}).getText().strip()
			inf = c.find('a', {'class': 'url summary'})
			link = self.base + inf['href']
			ch = inf['title'].strip()
			img = c.find('td', {'class': 'event'}).find('img')['src']
			if img.startswith('//'):
				img = 'https:' + img

			title = u'(%s) %s'%(country, ch)
			if cache.get(self.links, 2000, link) != []:
				out.append((link, title, img))
		return out
		

	def links(self, url):
		html = self.s.get(url).text
		links = re.findall('href\s*=\s*[\"\']([^\"\']+).+?streamframe.+?>([^<]+)', html)
		if len(links) < 1:
			links = []
			try:
				l = re.findall('streamframe.+?src\s*=\s*[\"\']([^\"\']+)', html)[0]
				if 'lowend' in l and not bool(re.search('stream/\d/', l)):
					pass
				else:
					links.append((l, 'Link #1'))
			except:
				pass
		else:
			ls = []
			for l in links:
				if not('lowend' in l[0] and not bool(re.search('stream/\d/', l[0]))):
					ls.append(l)
				
			links = ls	
		return links

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

	def next_page(self):
		page = self.url.split('/')[-1]

		url = self.url.replace('/{}'.format(page), '/{}'.format(str(int(page) + 1)))

		html = self.s.get(url).text

		if 'There are no events' in html:
			return None
		return url