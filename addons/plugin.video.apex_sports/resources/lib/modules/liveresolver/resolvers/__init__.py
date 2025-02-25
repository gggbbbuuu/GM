from os.path import dirname, basename, isfile, join
import glob
from resources.lib.modules.log_utils import log
import requests
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 OPR/73.0.3856.344'

def check(url, html):
	sup = []
	for module in __all__:
		exec('from . import *')
		r = eval('{}.Resolver()'.format(module))
		if r.isSupported(url, html):
			prio = 1
			try:
				prio = r.priority()
			except:
				pass

			sup.append((module, prio))

	sup.sort(key=lambda x:x[1])
	sup = [x[0] for x in sup]
	return sup


def resolve(url, referer='', referer_map={}):

	try:
		html = requests.get(url,allow_redirects=True, timeout=3, headers={'referer':referer, 'user-agent': USER_AGENT}).text
	except:
		return None

	modules = check(url, html)

	resolved = False
	for module in modules:
		exec('from . import *')
		r = eval('{}.Resolver()'.format(module))
		if module == 'wigistream':
			url_dict = r.resolve(url, html=html, referer=referer, referer_map=referer_map)
		else:
			url_dict = r.resolve(url, html=html, referer=referer)
		if url_dict:
			return url_dict
	return None
