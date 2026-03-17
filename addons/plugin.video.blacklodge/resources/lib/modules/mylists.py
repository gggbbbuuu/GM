# -*- coding: utf-8 -*-

import time

try: from sqlite3 import dbapi2 as database, IntegrityError
except: from pysqlite2 import dbapi2 as database, IntegrityError

from resources.lib.modules import control
from resources.lib.modules import log_utils


def insert(name, imdb, content, meta):
    try:
        t = int(time.time())

        control.makeFile(control.dataPath)
        dbcon = database.connect(control.mylistsFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS mylists (""type TEXT, ""imdb TEXT, ""title TEXT, ""meta TEXT, ""time INTEGER, ""UNIQUE(imdb)"");")
        dbcur.execute("INSERT INTO mylists Values (?, ?, ?, ?, ?)", (content, imdb, name, meta, t))
        dbcon.commit()
        control.refresh()
        control.infoDialog('Added to My List', heading=name, sound=True, icon=control.infoLabel('ListItem.Icon'))
    except IntegrityError:
        control.infoDialog('Content is already in the list', heading=name, sound=True, icon=control.infoLabel('ListItem.Icon'))
    except Exception:
        control.infoDialog('Error Adding to My List', heading=name, sound=True, icon='ERROR')
        log_utils.log('my_list_error', 1)


def remove(name, imdb):
    try:
        control.makeFile(control.dataPath)
        dbcon = database.connect(control.mylistsFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS mylists (""type TEXT, ""imdb TEXT, ""title TEXT, ""meta TEXT, ""time INTEGER, ""UNIQUE(imdb)"");")
        dbcur.execute("DELETE FROM mylists WHERE imdb = '%s'" % imdb)
        dbcon.commit()
        control.refresh()
        control.infoDialog('Removed from My List', heading=name, sound=True, icon=control.infoLabel('ListItem.Icon'))
    except:
        log_utils.log('my_list_remove_error', 1)


def check_list(content):
    try:
        control.makeFile(control.dataPath)
        dbcon = database.connect(control.mylistsFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS mylists (""type TEXT, ""imdb TEXT, ""title TEXT, ""meta TEXT, ""time INTEGER, ""UNIQUE(imdb)"");")
        dbcur.execute("SELECT * FROM mylists WHERE type = '%s'" % content)
        match = dbcur.fetchall()
        dbcon.commit()
        if match:
            return [m[1] for m in match]
        return []
    except:
        return []


