# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


from __future__ import absolute_import

import hashlib, json
from ast import literal_eval as evaluate
from tulip import control
from tulip.cache import clear
from tulip.compat import database, iteritems


def add(url, file_=control.bookmarksFile):

    try:

        data = json.loads(url)

        dbid = hashlib.md5()

        for i in data['bookmark']:
            try:
                dbid.update(str(i))
            except TypeError:
                dbid.update(i.encode('utf-8'))
        for i in data['action']:
            try:
                dbid.update(str(i))
            except TypeError:
                dbid.update(i.encode('utf-8'))

        dbid = str(dbid.hexdigest())

        item = dict((k,v) for k, v in iteritems(data) if not k == 'bookmark')
        item = repr(item)

        control.makeFile(control.dataPath)
        dbcon = database.connect(file_)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS bookmark (""dbid TEXT, ""item TEXT, ""UNIQUE(dbid)"");")
        dbcur.execute("DELETE FROM bookmark WHERE dbid = '{}'".format(dbid))
        dbcur.execute("INSERT INTO bookmark Values (?, ?)", (dbid, item))
        dbcon.commit()

    except Exception:

        pass


def delete(url, file_=control.bookmarksFile):

    try:

        data = json.loads(url)

        dbid = hashlib.md5()

        for i in data['delbookmark']:
            try:
                dbid.update(str(i))
            except TypeError:
                dbid.update(i.encode('utf-8'))

        for i in data['action']:
            try:
                dbid.update(str(i))
            except TypeError:
                dbid.update(i.encode('utf-8'))

        dbid = str(dbid.hexdigest())

        control.makeFile(control.dataPath)
        dbcon = database.connect(file_)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS bookmark (""dbid TEXT, ""item TEXT, ""UNIQUE(dbid)"");")
        dbcur.execute("DELETE FROM bookmark WHERE dbid = '{}'".format(dbid))
        dbcon.commit()

        control.refresh()

    except Exception:

        pass


def get(file_=control.bookmarksFile):

    try:

        control.makeFile(control.dataPath)
        dbcon = database.connect(file_)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM bookmark")
        items = dbcur.fetchall()

        try:
            items = [evaluate(i[1].encode('utf-8')) for i in items]
        except Exception:
            items = [evaluate(i[1]) for i in items]

        return items

    except Exception:

        return


__all__ = ['add', 'delete', 'get', 'clear']
