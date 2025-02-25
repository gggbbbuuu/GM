from bs4 import BeautifulSoup
import requests
import re
from ..plugin import Plugin
import xbmcgui

class Search(Plugin):
    name = "search"
    
    def get_list(self, url):
        if not url.startswith("search"):
            return False
        results = []
        url = "https://textbin.net/raw/vknsvg0g91"
        page = requests.get(url)

        soup = BeautifulSoup(page.text, "html.parser")

        dialog = xbmcgui.Dialog()
        d = dialog.input('Enter Search Term', type=xbmcgui.INPUT_ALPHANUM)
        for item in soup.find_all('item'):
            title = item.title.text
            summary = item.summary.text
            links = re.findall(r"(https?://.*?)(?:\s|$)", str(summary))
            if not links:
                continue
            if title == 'Add Multiple Sources':
                continue
            if d.lower() in summary.lower():
                results.append(str(item))
            #if d.lower() in title.lower():
            #    results.append(str(item))
        if results:
        	return f'<xml>{"".join(results)}</xml>'
        else:
        	return "<xml><item><title>Sorry No Source Found</title><link></link></item></xml>"
