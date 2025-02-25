#!/usr/bin/env python3
"""Search whole addon through sqlite database file."""

import json
import os
import sqlite3
import time
import sys
import xbmcvfs
import xbmcaddon

from ..plugin import Plugin
from ..DI import DI

db_url = ""
dest_file = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path'))+"search.db"  # Edit - Added addon path 

class searchdb(Plugin):
    name = "Search db"
    priority = -1  # Edit - Lowered priority was conflicting with http plugin

    def fetch_db(self) -> None:
        response = DI.session.get(db_url)
        changed = response.headers["Last-Modified"]
        changed_struct = time.strptime(changed, "%a, %d %b %Y %H:%M:%S GMT")
        epoch_changed = int(time.mktime(changed_struct))
        if (
            not os.path.exists(dest_file)
            or int(os.path.getmtime(dest_file)) < epoch_changed
        ):
            with open(dest_file, "wb") as f:
                f.write(response.content)

    def from_keyboard(self, default_text="", header="Search"):
        from xbmc import Keyboard

        kb = Keyboard(default_text, header, False)
        kb.doModal()
        if kb.isConfirmed():
            if kb.getText() == "":
                return None
            return kb.getText()

    def get_list(self, url):
        if url == "searchdb":
            search_term = self.from_keyboard()
            # Edit - indented block
            if not search_term:
                sys.exit()
            self.fetch_db()
            con = sqlite3.connect(dest_file)
            cur = con.cursor()
            db_items = cur.execute(
                'SELECT * from search where title like "%%%s%%"' % search_term
            ).fetchall()
            items = [json.loads(item[1]) for item in db_items]
            return json.dumps({"items": items})
