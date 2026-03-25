# -*- coding: utf-8 -*-

import time

try: from sqlite3 import dbapi2 as database, IntegrityError
except: from pysqlite2 import dbapi2 as database, IntegrityError

from resources.lib.modules import control
from resources.lib.modules import cleantitle
from resources.lib.modules import imdb_api
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


def add_imdb_list():
    list_id = control.inputDialog(heading='List ID ( ls[I]XXXXXXX[/I] )', kb='num')
    if not list_id or len(list_id) < 6:
        return control.infoDialog('Invalid List ID', sound=True, icon='ERROR')
    list_id = 'ls%s' %  list_id
    params = {'list': list_id, 'titleType': 'movie,tvMovie,short,video,tvSeries,tvMiniSeries', 'sort': 'POPULARITY,ASC'}
    try:
        lst = imdb_api.get_customlist(1, '', params, True)
        if not lst['titleListItemSearch']:
            return control.infoDialog('Could not populate list %s' % list_id, sound=True, icon='ERROR')
        list_name = cleantitle.normalize(lst['name']['originalText'])
        author = cleantitle.normalize(lst['author']['username']['text'])
    except:
        return control.infoDialog('Could not populate list %s' % list_id, sound=True, icon='ERROR')

    try:
        control.makeFile(control.dataPath)
        dbcon = database.connect(control.mylistsFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS imdbLists (""id TEXT, ""name TEXT, ""author TEXT, ""UNIQUE(id)"");")
        dbcur.execute("INSERT INTO imdbLists Values (?, ?, ?)", (list_id, list_name, author))
        dbcon.commit()
        control.infoDialog('List added!', heading=list_name, sound=True)
        control.refresh()
    except IntegrityError:
        control.infoDialog('List is already added', heading=list_name, sound=True, icon='INFO')
    except Exception:
        control.infoDialog('Error adding list', heading=list_name, sound=True, icon='ERROR')
        log_utils.log('my_list_error', 1)


def del_imdb_list(list_id):
    control.makeFile(control.dataPath)
    dbcon = database.connect(control.mylistsFile)
    dbcur = dbcon.cursor()
    dbcur.execute("DELETE FROM imdbLists WHERE id = '%s'" % list_id)
    dbcon.commit()
    control.refresh()
    control.infoDialog('List %s removed' % list_id, sound=True, icon='INFO')

