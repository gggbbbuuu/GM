import re, json
import requests
from resources.lib.modules.log_utils import log
from resources.lib.modules import control
class info():
	def __init__(self):
		self.mode = 'nbacom'
		self.name = 'nba.com'
		self.icon = 'nba.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = True
		self.categorized = True
		self.multilink = False


class main():
	def __init__(self, url = ''):
		self.url = url

	def categories(self):
		out = []

		list_url = 'https://content-api-prod.nba.com/public/1/endeavor/video-list/collection/{}'
		url = 'https://content-api-prod.nba.com/public/1/endeavor/layout/watch/landing'
		cats = json.loads(requests.get(url).text)['results']['carousels']
		for c in cats:
			if c['type'] != 'video_carousel':
				continue
			u = list_url.format(c['value']['slug'])
			title = c['title'].title()
			out.append((u, title, info().icon))

		return out

	def events(self, url):
		self.url = url
		html = requests.get(url).text
		query = json.loads(html)
		results = query['results']['videos']
		items=[]
		for i in range(len(results)):
			link =results[i]['program']['id']

			title=results[i]['title']
			thumb=results[i]['image']

			
			items+=[(link, title,thumb)]
		return items

	def resolve(self, link):

		url = 'https://watch.nba.com/service/publishpoint?type=video&id={}&format=json'.format(link)
		js = requests.post(url)
		js = json.loads(js.text)
		return js['path']	    

	def next_page(self):
		
		try:
			current = re.findall("page=(\d+)",self.url)[0]
		except:
			current = 1
			next_page = self.url + '?page=2'
			return next_page
		link = re.sub('\?page\=\d+', '', self.url)
		next_page = link + '?page=' + str(int(current) + 1)
		
		return next_page


