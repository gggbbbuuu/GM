from ..plugin import Plugin
import re
import operator

good_files = ([
    'fluxustv',
    'ftviptv',
     ])  


class m3u(Plugin):
	name = "m3u"
	description = "add support for m3u lists"
	priority = 2
    
	def parse_list(self, url: str, response):
		item_list = []
		if url.endswith(".m3u") or url.endswith(".m3u8") or any(check in url.lower() for check in good_files) : 
			response = response.rstrip()
			match = re.compile(r'#EXTINF:(.+?),(.*?)[\n\r]+([^\n]+)').findall(response)
			for other,channel_name,stream_url in match:
				if 'tvg-logo' in other:
					thumbnail = self.re_me(other,'tvg-logo=[\'"](.*?)[\'"]')
				if thumbnail:
					thumbnail = thumbnail
				else:
					thumbnail = ''
				item = {'title': channel_name, 'link': stream_url, 'thumbnail': thumbnail, 'type': 'item'}
				item_list.append(item)
		item_list.sort(key = operator.itemgetter('title'), reverse = False)
		return item_list
    
	def re_me(self, data, re_patten):
		match = ''
		m = re.search(re_patten, data)
		if m != None:
		  	match = m.group(1)
		else:
		  	match = ''
		return match