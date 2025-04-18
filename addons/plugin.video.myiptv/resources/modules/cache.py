﻿# -*- coding: utf-8 -*-

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


import re, hashlib, time
from ast import literal_eval as evaluate
import six
try:
    from sqlite3 import dbapi2 as database
except:
    # noinspection PyUnresolvedReferences
    from pysqlite2 import dbapi2 as database

from resources.modules import control


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
    except:
        pass

    try:
        table = table['table']
    except:
        table = 'rel_list'

    try:
        control.makeFile(control.dataPath)
        dbcon = database.connect(control.cacheFile)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM {tn} WHERE func = '{f}' AND args = '{a}'".format(tn=table, f=f, a=a))
        match = dbcur.fetchone()

        response = evaluate(six.ensure_str(match[2], errors='replace'))

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
        r = repr(r)
        t = int(time.time())
        dbcur.execute("CREATE TABLE IF NOT EXISTS %s (""func TEXT, ""args TEXT, ""response TEXT, ""added TEXT, ""UNIQUE(func, args)"");" % table)
        dbcur.execute("DELETE FROM %s WHERE func = '%s' AND args = '%s'" % (table, f, a))
        dbcur.execute("INSERT INTO %s Values (?, ?, ?, ?)" % table, (f, a, r, t))
        dbcon.commit()
    except:
        pass

    try:
        return evaluate(six.ensure_str(r, errors='replace'))
    except:
        pass


def timeout(definition, *args, **table):

    try:
        response = None

        f = repr(definition)
        f = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i in args:
            if i is None: i = ''
            a.update(six.ensure_binary(i, errors='replace'))
        a = str(a.hexdigest())
    except:
        pass

    try:
        table = table['table']
    except:
        table = 'rel_list'

    try:
        control.makeFile(control.dataPath)
        dbcon = database.connect(control.cacheFile)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM %s WHERE func = '%s' AND args = '%s'" % (table, f, a))
        match = dbcur.fetchone()
        return int(match[3])
    except:
        return


def clear(table=None, withyes=True):

    try:
        # control.idle()

        if table is None:
            table = ['rel_list', 'token', 'rel_lib']
        elif not type(table) == list:
            table = [table]

        if withyes:

            yes = control.yesnoDialog(control.lang(30401).encode('utf-8'), '', '')

            if not yes:
                return

        else:

            pass

        dbcon = database.connect(control.cacheFile)
        dbcur = dbcon.cursor()

        for t in table:
            try:
                dbcur.execute("DROP TABLE IF EXISTS %s" % t)
                dbcur.execute("VACUUM")
                dbcon.commit()
            except:
                pass

        control.infoDialog('Έγινε εκκαθάριση μνήμης Cache'.encode('utf-8'))
    except:
        pass


def delete(dbfile=control.cacheFile, withyes=True):

    if withyes:

        yes = control.yesnoDialog(control.lang(30401).encode('utf-8'), '', '')

        if not yes:
            return

    else:

        pass

    control.deleteFile(dbfile)

    control.infoDialog('Έγινε διαγραφή αρχειού cache.db'.encode('utf-8'))


