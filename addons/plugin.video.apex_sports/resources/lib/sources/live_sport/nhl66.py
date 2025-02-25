# -*- coding: UTF-8 -*-
from resources.lib.modules import control, constants
import sys, json, xbmcgui, requests
from resources.lib.modules.log_utils import log

# python 2 doesn't support date.datetime.timestamp()
if sys.version_info[0] < 3 or sys.version_info[1] < 4:
    # python version < 3.3
    import time
    def timestamp(date):
        return time.mktime(date.timetuple())
else:
    def timestamp(date):
        return date.timestamp()
        
class info():
	def __init__(self):
		self.mode = 'nhl66'
		self.name = 'NHL66'
		self.icon = 'nhl.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = False
		self.categorized = False
		self.multilink = False


class main():
	def __init__(self,url = 'https://api.nhl66.ir/api/sport/schedule'):
		self.base = 'https://nhl66.ir/'
		self.url = url
		self.headers = {'referer': self.base, 'user-agent': constants.USER_AGENT}

	def events(self):
		result = requests.get(self.url, headers=self.headers).text
		games = json.loads(result)['games']

		sortt = {'x':99999999999999999999}
		out = []
		live_out = [('x', u'[COLOR blue]► Following games[/COLOR]')]
		replays = [('x', u'[COLOR blue]► Replays[/COLOR]')]

		for g in games:
			url = g['id']
			start, timestamp = self.convert_time(g['start_datetime'])
			sortt[url] = timestamp
			live = g['status'] == 'Live'
			replay = g['status'] == 'Final'
			if live:
				title = u'[COLOR red](LIVE)[/COLOR] [B]{} - {}[/B]'.format(g['home_name'], g['away_name'])
			else:
				title = u'({}) [B]{} - {}[/B]'.format(start, g['home_name'], g['away_name'])
			
			
			if g['streams'] != []:
				if live:
					live_out.append((url, title))
				elif replay:
					replays.append((url, title))
				else:
					out.append((url, title))
		replays.sort(reverse=True, key=lambda x: sortt[x[0]])
		out = live_out + out + replays
		return out


	@staticmethod
	def convert_time(t):
		t1, t2 = t.split('T')
		year, month, day = t1.split('-')
		hour, minute, _ = t2.split(':')
		import datetime
		import pytz
		d = pytz.timezone(str(pytz.timezone('Europe/London'))).localize(datetime.datetime(2000 , int(month), int(day), hour=int(hour), minute=int(minute)))
		timezona= control.setting('timezone_new')
		my_location = pytz.timezone(constants.get_zone(int(timezona)))
		convertido=d.astimezone(my_location)
		fmt = "%m/%d %H:%M"
		time=convertido.strftime(fmt)
		return time, timestamp(convertido)

	def resolve(self,url):
		if url == 'x':
			return ' '
		result = requests.get(self.url, headers=self.headers).text
		games = json.loads(result)['games']

		for g in games:
			if str(g['id']) == str(url):
				streams = g['streams']
				dialog = xbmcgui.Dialog()
				lst = [s['name'] for s in streams]
				index = dialog.select("Select stream", lst)
				if index == -1:
					return ' '
				media_id = g['streams'][index]['mediaid']

				return 'https://api.nhl66.ir/api/get_master_url/{}.m3u8|Referer=https://nhl66.ir'.format(media_id), True
		return ' '