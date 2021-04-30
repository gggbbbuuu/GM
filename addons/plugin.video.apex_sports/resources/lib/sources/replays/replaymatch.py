from resources.lib.modules import webutils, control, constants
from resources.lib.modules.log_utils import log
import re
import requests
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode


class info():
	def __init__(self):
		self.mode = 'replaymatch'
		self.name = 'replaymatches.net'
		self.icon = 'icons/soccer.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = True
		self.categorized = False
		self.multilink = True


class main():
	def __init__(self, url = 'http://www.replaymatches.net'):
		self.base = 'http://www.replaymatches.net'
		self.url = url


	def events(self):
		out = []
		import requests
		s = requests.session()
		html = s.get(self.url).text
		soup = webutils.bs(html)
		articles = soup.findAll('article', {'class': 'post hentry'})
		for article in articles:
			s = article.findAll('img')[1]
			title = s['alt']
			img = s['src']
			url = article.find('h2').find('a')['href']
			out.append((url, title, img))
		

		return out

	
	def links(self, url):
		html = requests.get(url).text
		soup = webutils.bs(html)
		try:
			img = soup.find('meta', {'property':'og:image'})['content']
		except:
			img = control.icon_path(info().icon)
		out=[]
		
		videos = soup.findAll('a', {'class':'link-iframe'})
		for v in videos:
			url = v['href']
			title = v.getText()
			img = info().icon
			out.append((url, title, img))
		
		if len(out) == 0:
			ifr = re.findall('iframe.+?src\s*=\s*[\"\']([^\"\']+)', html)[0]
			out.append((ifr, 'Link 1', img))

		return out

	def resolve(self,url):
		if 'hdmat' in url:
			from resources.lib.modules import liveresolver
			d = liveresolver.Liveresolver().resolve(url)
			if d:
				return '{}|{}'.format(d['url'], urlencode(d['headers'])).replace('0.m3u8', '720p.m3u8')
		try:
			import resolveurl
			res = resolveurl.resolve(url)
		except:
			res = ' '
		if not res:
			from resources.lib.modules import liveresolver
			d = liveresolver.Liveresolver().resolve(url)
			if d:
				return '{}|{}'.format(d['url'], urlencode(d['headers']))
			else:
				return ' '

		return res
		
	def next_page(self):
		try:
			page = int(self.url.split('##')[1])
		except:
			page = 1

		html = requests.get(self.url).text
		next = webutils.bs(html).findAll('a', {'class': 'blog-pager-older-link'})[-1]['href']
		next =  next + '##%s'%(page+1)
		return next

