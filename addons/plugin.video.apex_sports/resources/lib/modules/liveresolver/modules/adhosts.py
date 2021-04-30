import re
import requests
from resources.lib.modules import cache

try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2

HOSTS_URL = 'https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts'

def getit():
	return requests.get(HOSTS_URL).text

def isAd(host):
	hst = cache.get(getit, 2880)
	h = urlparse(host).netloc
	return (h in hst)