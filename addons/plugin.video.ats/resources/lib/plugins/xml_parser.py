from ..plugin import Plugin
import xml.etree.ElementTree as ET
from typing import Dict, Union


class xml(Plugin):
    name = "xml"
    description = "add support for xml jen format"
    priority = 0

    def parse_list(self, url: str, response):
        if url.startswith("https://") or url.endswith(".xml") or response.startswith("<xml>"):
            response = response
            try:
                xml = ET.fromstring(response)
            except ET.ParseError:
                xml = ET.fromstringlist(["<root>", response, "</root>"])
            itemlist = []
            if xml.tag in ["dir", "item"]:
                itemlist.append(self._handle_item(xml))
                return itemlist
            for item in xml:
                itemlist.append(self._handle_item(item))
            return itemlist

    def _handle_item(self, item: ET.Element) -> Dict[str, str]:
        result = {child.tag: child.text for child in item}
        result["type"] = item.tag
        return result
