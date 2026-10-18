# -*- coding: utf-8 -*-

'''
    Tulip routine libraries, based on lambda's lamlib
    Author Twilight0

        License summary below, for more details please read license.txt file

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 2 of the License, or
        (at your option) any later version.
        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.
        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''


import re, hashlib, time, os, threading
import xbmc, xbmcaddon, xbmcgui, xbmcvfs
from ast import literal_eval as evaluate
import six
try:
    from sqlite3 import dbapi2 as database
except:
    # noinspection PyUnresolvedReferences
    from pysqlite2 import dbapi2 as database

if six.PY2:
    translatePath = xbmc.translatePath
elif six.PY3:
    translatePath = xbmcvfs.translatePath
addon = xbmcaddon.Addon('plugin.program.downloader')
cacheFile = translatePath(os.path.join(addon.getAddonInfo("path"), "cache.db"))
icon = translatePath(addon.getAddonInfo("icon"))
execute = xbmc.executebuiltin
dialog = xbmcgui.Dialog()

_local = threading.local()

def _get_conn():
    conn = getattr(_local, 'conn', None)
    if conn is None:
        conn = database.connect(cacheFile, timeout=30)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=30000")
        except Exception:
            pass
        _local.conn = conn
    return conn

def get(definition, time_out, *args, **table):
    try:

        response = None

        f = repr(definition)
        f = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i in args:
            str_i = str(i)
            if "'Authorization': 'Bearer" in str_i:
                str_i = re.sub(r"'Authorization': 'Bearer.+?'","",str_i)
            elif "requests.sessions.Session" in str_i:
                continue
            try:
                a.update(str_i.encode('utf-8'))
            except:
                a.update(str_i)
        a = str(a.hexdigest())

    except Exception:

        pass

    try:
        table = table['table']
    except:
        table = 'mac_player'

    try:
        dbcon = _get_conn()
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM {tn} WHERE func = ? AND args = ?".format(tn=table), (f, a))
        match = dbcur.fetchone()

        try:
            response = evaluate(match[2])
        except:
            response = evaluate(match[2].encode('utf-8'))

        t1 = int(match[3])
        t2 = int(time.time())
        update = (abs(t2 - t1) / 3600) >= int(time_out)
        if not update:
            return response
    except:
        pass

    try:
        r = definition(*args)
        if (r is None or r == []) and response is not None:
            return response
        elif r is None or r == []:
            return r
    except:
        return

    try:
        r_repr = repr(r)
        t = int(time.time())
        dbcon = _get_conn()
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS %s (""func TEXT, ""args TEXT, ""response TEXT, ""added TEXT, ""UNIQUE(func, args)"");" % table)
        dbcur.execute("DELETE FROM %s WHERE func = ? AND args = ?" % table, (f, a))
        dbcur.execute("INSERT INTO %s Values (?, ?, ?, ?)" % table, (f, a, r_repr, t))
        dbcon.commit()
    except:
        pass

    return r


def timeout(definition, *args, **table):

    try:
        response = None

        f = repr(definition)
        f = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i in args:
            try:
                a.update(str(i).encode('utf-8'))
            except:
                a.update(str(i))
        a = str(a.hexdigest())
    except:
        pass

    try:
        table = table['table']
    except:
        table = 'mac_player'

    try:

        dbcon = _get_conn()
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM {tn} WHERE func = ? AND args = ?".format(tn=table), (f, a))
        match = dbcur.fetchone()
        return int(match[3])

    except Exception:

        return


def clear(table=None):
    try:
        execute('Dialog.Close(busydialog)')

        if table == None: table = ['mac_player', 'token', 'rel_lib']
        elif not type(table) == list: table = [table]

        # yes = dialog.yesno(heading=addon.getAddonInfo('name'), line1=addon.getLocalizedString(30401).encode('utf-8'))
        # if not yes: return

        dbcon = _get_conn()
        dbcur = dbcon.cursor()

        for t in table:
            try:
                dbcur.execute("DROP TABLE IF EXISTS %s" % t)
                dbcur.execute("VACUUM")
                dbcon.commit()
            except:
                pass

        # dialog.notification(heading=addon.getAddonInfo('name'), message='Cleared', icon=icon, time=2000, sound=False)
    except:
        pass


