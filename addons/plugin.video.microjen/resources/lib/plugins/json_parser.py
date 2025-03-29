from ..plugin import Plugin
import json
import xbmc

class json_parser(Plugin):
    name = "json_parser"
    description = "add json format support"
    priority = 0

    def parse_list(self, url: str, response):
        if url.endswith(".json") or url.endswith(".zip") or '"items": [' in response :
            response = "".join([s for s in response.strip().splitlines(True) if s.strip()])#remove empty lines from response
            if not response.startswith('{'):
                response = '{'+response
            if not response.endswith('}'):
                response = response+'}'
            try:
                itms = [i for i in json.loads(response)["items"] if not i.get("enabled","true").lower()=="false"]
                itms_2 = []
                for itm in itms:
                    try:
                        itm.update({"orig": url})
                    except:
                        pass
                    itms_2.append(itm)
                return itms_2
            except:
                xbmc.log(f"invalid json: {response}", xbmc.LOGINFO)
                return [
                        { 
                            "title": "[COLOR khaki]Ρυθμίσεις Microjen[/COLOR]", 
                            "type": "item", 
                            "link": "settings"
                        }, 
                        {
                            "type": "item",
                            "title": "[COLOR khaki]Clear Cache[/COLOR]",
                            "link": "clear_cache_silent"
                        }, 
                        ]

