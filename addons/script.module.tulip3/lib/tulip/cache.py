# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''


from __future__ import absolute_import, print_function, division

import re
import functools
import time
import hashlib
import os
import shutil
try:
    from kodi_six import xbmcvfs
except Exception:
    xbmcvfs = None

from ast import literal_eval as evaluate
from tulip.compat import str, database, pickle

try:
    from tulip import control
    from tulip.log import log_debug
    cache_path = control.join(control.dataPath, 'cache')
except Exception:
    control = None
    cache_path = os.path.join(os.curdir, 'function_cache')

ENABLED = True
SECONDS = 1
MINUTES = 60
HOURS = 3600


# noinspection PyUnboundLocalVariable
def get(function_, duration, *args, **table):

    try:

        response = None

        f = repr(function_)
        f = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i in args:
            try:
                a.update(str(i))
            except TypeError:
                a.update(i.encode('utf-8'))
        a = str(a.hexdigest())

    except Exception:

        pass

    try:
        table = table['table']
    except Exception:
        table = 'rel_list'

    try:

        if control:
            control.makeFile(control.dataPath)
            dbcon = database.connect(control.cacheFile)
        else:
            db_file = os.path.join(os.path.curdir, 'cache.db')
            dbcon = database.connect(db_file)

        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM {tn} WHERE func = '{f}' AND args = '{a}'".format(tn=table, f=f, a=a))
        match = dbcur.fetchone()

        try:
            response = evaluate(match[2].encode('utf-8'))
        except AttributeError:
            response = evaluate(match[2])

        t1 = float(match[3])
        t2 = time.time()
        update = (abs(t2 - t1) / float(HOURS)) >= float(duration)
        if not update:
            return response

    except Exception:

        pass

    try:

        r = function_(*args)
        if (r is None or r == []) and response is not None:
            return response
        elif r is None or r == []:
            return r

    except Exception:
        return

    try:

        r = repr(r)
        t = int(time.time())
        dbcur.execute("CREATE TABLE IF NOT EXISTS {} (""func TEXT, ""args TEXT, ""response TEXT, ""added TEXT, ""UNIQUE(func, args)"");".format(table))
        dbcur.execute("DELETE FROM {0} WHERE func = '{1}' AND args = '{2}'".format(table, f, a))
        dbcur.execute("INSERT INTO {} Values (?, ?, ?, ?)".format(table), (f, a, r, t))
        dbcon.commit()

    except Exception:
        pass

    try:
        return evaluate(r.encode('utf-8'))
    except Exception:
        return evaluate(r)


# noinspection PyUnboundLocalVariable
def timeout(function_, *args, **table):

    try:

        f = repr(function_)
        f = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i in args:
            try:
                a.update(str(i))
            except TypeError:
                a.update(i.encode('utf-8'))
        a = str(a.hexdigest())
    except Exception:
        pass

    try:
        table = table['table']
    except Exception:
        table = 'rel_list'

    try:

        if control:

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.cacheFile)

        else:

            db_file = os.path.join(os.path.curdir, 'cache.db')
            dbcon = database.connect(db_file)

        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM {tn} WHERE func = '{f}' AND args = '{a}'".format(tn=table, f=f, a=a))
        match = dbcur.fetchone()
        return int(match[3])

    except Exception:

        return


def clear(table=None, withyes=False, notify=True, file_=None, label_yes_no=30401, label_success=30402):

    if file_ is None:
        if control:
            file_ = control.cacheFile
        else:
            file_ = os.path.join(os.path.curdir, 'cache.db')

    try:
        if control:
            control.idle()

        if table is None:
            table = ['rel_list', 'rel_lib']
        elif not type(table) == list:
            table = [table]

        if withyes and control:

            try:
                yes = control.yesnoDialog(control.lang(label_yes_no).encode('utf-8'), '', '')
            except Exception:
                yes = control.yesnoDialog(control.lang(label_yes_no), '', '')

            if not yes:
                return

        dbcon = database.connect(file_)
        dbcur = dbcon.cursor()

        for t in table:
            try:
                dbcur.execute("DROP TABLE IF EXISTS {0}".format(t))
                dbcur.execute("VACUUM")
                dbcon.commit()
            except Exception:
                pass

        if control and notify:
            control.infoDialog(control.lang(label_success).encode('utf-8'))
    except Exception:
        pass


def delete(withyes=True, label_yes_no=30401, label_success=30402):

    if withyes:

        yes = control.yesnoDialog(control.lang(label_yes_no).encode('utf-8'), '', '')

        if not yes:
            return

    else:

        pass

    control.deleteFile(control.cacheFile)

    control.infoDialog(control.lang(label_success).encode('utf-8'))

# Functions below shamelessly taken and adapted from ResolveURL, so thanks to all of its contributors

class FunctionCache:

    def __init__(self, protocol=pickle.HIGHEST_PROTOCOL):

        if not os.path.exists(cache_path):
            os.makedirs(cache_path)

        self.protocol = protocol

    def reset_cache(self, notify=False, label_success=30402):

        try:
            shutil.rmtree(cache_path)
            if notify and control:
                control.infoDialog(control.lang(label_success).encode('utf-8'))
            return True
        except Exception as e:
            if control:
                log_debug('Failed to create cache: {0}: {1}'.format(cache_path, e))
            else:
                print('Failed to create cache: {0}: {1}'.format(cache_path, e))
            return False

    def _get_filename(self, name, args, kwargs):

        _name = hashlib.md5(name.encode('utf-8')).hexdigest()
        _args = hashlib.md5(str(args).encode('utf-8')).hexdigest()
        _kwargs = hashlib.md5(str(kwargs).encode('utf-8')).hexdigest()

        return _name + _args + _kwargs

    def _load(self, name, args=None, kwargs=None, limit=60):
        if not ENABLED or limit <= 0:
            return False, None

        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        now = time.time()
        max_age = now - limit

        filename = os.path.join(cache_path, self._get_filename(name, args, kwargs))
        if os.path.exists(filename):
            if xbmcvfs:
                mtime = xbmcvfs.Stat(filename).st_mtime()
            else:
                mtime = os.path.getmtime(filename)

            if mtime >= max_age:
                with open(filename, 'rb') as file_handle:
                    payload = file_handle.read()

                return True, pickle.loads(payload)

        return False, None

    def _save(self, name, args=None, kwargs=None, result=None):

        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        try:
            payload = pickle.dumps(result, protocol=self.protocol)

            filename = os.path.join(cache_path, self._get_filename(name, args, kwargs))
            with open(filename, 'wb') as file_handle:
                file_handle.write(payload)

            return True

        except:  # pylint: disable=bare-except
            return False

    def cache_method(self, limit, limit_mode=MINUTES):

        """
        Uses pickle to cache a class method's returned result. Limit is in seconds, limit_mode is the multiplier
        :param limit: int
        :param limit_mode: int
        :return: bytes
        """

        limit = limit * limit_mode

        def wrap(func):

            @functools.wraps(func)
            def memoizer(*args, **kwargs):
                if args:
                    klass, rargs = args[0], args[1:]
                    name = '%s.%s.%s' % (klass.__module__, klass.__class__.__name__, func.__name__)
                else:
                    name = func.__name__
                    rargs = args

                cached, payload = self._load(name, rargs, kwargs, limit=limit)
                if cached:
                    return payload

                payload = func(*args, **kwargs)
                if ENABLED and limit > 0:
                    self._save(name, rargs, kwargs, payload)

                return payload

            return memoizer

        return wrap

    def cache_function(self, limit, limit_mode=MINUTES):

        """
        Uses pickle to cache a function's returned result. Limit is in seconds, limit_mode is the multiplier
        :param limit: int
        :param limit_mode: int
        :return: bytes
        """

        limit = limit * limit_mode

        def wrap(func):

            @functools.wraps(func)
            def memoizer(*args, **kwargs):
                name = func.__name__

                cached, payload = self._load(name, args, kwargs, limit=limit)
                if cached:
                    return payload

                payload = func(*args, **kwargs)
                if ENABLED and limit > 0:
                    self._save(name, args, kwargs, payload)

                return payload

            return memoizer

        return wrap
