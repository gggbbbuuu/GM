from resources.lib.modules import control, constants
from resources.lib.modules.log_utils import log
import re, json
import requests

class info():
	def __init__(self):
		self.mode = 'fullmatchesandshows'
		self.name = 'fullmatchesandshows.com'
		self.icon = 'fms.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = True
		self.categorized = False
		self.multilink = True


class main():
	
	def __init__(self,url = 'https://www.fullmatchesandshows.com'):
		self.base = 'https://www.fullmatchesandshows.com'
		self.url = url
		self.post_url = 'https://www.fullmatchesandshows.com/wp-admin/admin-ajax.php?td_theme_name=Newspaper&v=10.3.7'
		self.postData = self.get_post(requests.get(self.url).text)
		self.postData['td_filter_value'] =  self.url.split('##')[0]
		try:
			self.postData['td_current_page'] = self.url.split('##')[1]
		except:
			self.postData['td_current_page'] = '1'


	def get_post(self,content):
		action = 'td_ajax_block'
		block_type = re.compile('block_type\s*=\s*[\"\']([^\"\']+)').findall(content)[0]
		td_atts = re.compile('\.atts\s*=\s*\'([^\']+)').findall(content)[0]
		td_block_id = re.findall('td\-block\-uid\s*=\s*[\"\']([^\"\']+)', content)[0]
		td_column_number = re.compile('column_number\s*=\s*[\"\']([^\"\']+)').findall(content)[0]
		nonce = re.findall('tdblocknonce\s*=\s*[\"\']([^\"\']+)', content, re.I)[0]
		data = {
			'action':action,
			'block_type':block_type,
			'td_atts':td_atts,
			'td_block_id':td_block_id,
			'td_column_number':td_column_number,
			'td_magic_token':nonce
		}
		return data


	def events(self):
		out = []
		import requests
		s = requests.session()
		s.get(self.base)
		html = s.post(self.post_url,data=self.postData, headers={'user-agent': constants.USER_AGENT, 'referer':self.base, 'x-requested-with':'XMLHttpRequest'}).text
		j = json.loads(html)
		data = j['td_data']
		items = re.findall('href=[\"\']([^\"\']+)[\"\'].+?title=[\"\']([^\"\']+)[\"\'].+?img.+?src=[\"\']([^\"\']+)[\"\']',data)
		for item in items:
			try:
				import HTMLParser
				parser = HTMLParser.HTMLParser()
				unescape = parser.unescape
			except:
				import html
				unescape = html.unescape
			title = unescape(item[1])
			out.append((item[0], title, item[2]))
		

		return out

	
	def links(self, url):
		out=[]
		html = requests.get(url).text
		try:
			img = re.findall('class="wpb_wrapper">\s*<a href=[\"\']([^\"\']+)[\"\']',html)[0]
		except:
			img = control.icon_path(info().icon)

		links = re.findall('(?:acp_title[\"\']>|h.>)([^<]+)<\/.+?\s*.+?iframe.+?src\s*=\s*[\"\']([^\"\']+)', html)
		link_dict = {k:v for v,k in links}
		try:
			import resolveurl
		except:
			return []
		videos = resolveurl.filter_source_list([l[1] for l in links])
		for v in videos:
			url = v
			title = link_dict[v]
			out.append((url, title, img))
				
		return out

	def resolve(self,url):
		import resolveurl
		try:
			res = resolveurl.resolve(url)
		except:
			res = ' '
		if not res:
			res = ' '
		
		return res
		
	def next_page(self):
		try:
			page = int(self.url.split('##')[1])
		except:
			page=1
		next = self.postData['td_filter_value'] + '##%s'%(page+1)
		return next

