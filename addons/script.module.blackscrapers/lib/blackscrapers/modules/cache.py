# -*- coding: utf-8 -*-

from __future__ import absolute_import

import hashlib
import re
import time
import os
from ast import literal_eval
import six

try:
    from sqlite3 import dbapi2 as db, OperationalError
except ImportError:
    from pysqlite2 import dbapi2 as db, OperationalError

from blackscrapers.modules import control, utils

if six.PY2:
    str = unicode
elif six.PY3:
    str = unicode = basestring = str

cache_table = 'cache'
data_path = control.transPath(control.addon('plugin.video.blacklodge').getAddonInfo('profile'))

def get(function, duration, *args):
    # type: (function, int, object) -> object or None
    """
    Gets cached value for provided function with optional arguments, or executes and stores the result
    :param function: Function to be executed
    :param duration: Duration of validity of cache in hours
    :param args: Optional arguments for the provided function
    """

    try:
        key = _hash_function(function, args)
        cache_result = cache_get(key)
        if cache_result:
            if _is_cache_valid(cache_result['date'], duration):
                return literal_eval(six.ensure_str(cache_result['value'], errors='replace'))

        fresh_result = repr(function(*args))
        if not fresh_result or fresh_result in ['None', '', '[]', '{}']:
            # If the cache is old, but we didn't get fresh result, return the old cache
            if cache_result:
                return cache_result
            return [] # rli needs an epmty list loaded in case of no content

        cache_insert(key, fresh_result)
        return literal_eval(six.ensure_str(fresh_result, errors='replace'))
    except Exception:
        return [] # rli needs an epmty list loaded in case of no content

def timeout(function_, *args):
    try:
        key = _hash_function(function_, args)
        result = cache_get(key)
        return int(result['date']) if result else 0
    except Exception:
        return 0

def cache_get(key):
    # type: (str, str) -> dict or None
    try:
        cursor = _get_connection_cursor()
        cursor.execute("SELECT * FROM %s WHERE key = ?" % cache_table, [key])
        return cursor.fetchone()
    except OperationalError:
        return None

def cache_insert(key, value):
    # type: (str, str) -> None
    cursor = _get_connection_cursor()
    now = int(time.time())
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS %s (key TEXT, value TEXT, date INTEGER, UNIQUE(key))"
        % cache_table
    )
    update_result = cursor.execute(
        "UPDATE %s SET value=?,date=? WHERE key=?"
        % cache_table, (value, now, key))

    if update_result.rowcount == 0:
        cursor.execute(
            "INSERT INTO %s Values (?, ?, ?)"
            % cache_table, (key, value, now)
        )

    cursor.connection.commit()

def cache_clear():
    try:
        cursor = _get_connection_cursor()

        for t in [cache_table, 'rel_list', 'rel_lib']:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass

def cache_clear_meta():
    try:
        cursor = _get_connection_cursor_meta()

        for t in ['meta']:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass

def cache_clear_providers():
    try:
        cursor = _get_connection_cursor_providers()

        for t in ['rel_src', 'rel_url']:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass

def cache_clear_search(table):
    try:
        if table == 'all':
            table = ['tvshow', 'movies', 'people']
        elif not isinstance(table, list):
            table = [table]

        cursor = _get_connection_cursor_search()

        for t in table:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass

def cache_clear_all():
    cache_clear()
    cache_clear_meta()
    cache_clear_providers()

def _get_connection_cursor():
    conn = _get_connection()
    return conn.cursor()

def _get_connection():
    control.makeFile(data_path)
    conn = db.connect(os.path.join(data_path, 'cache.db'))
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_meta():
    conn = _get_connection_meta()
    return conn.cursor()

def _get_connection_meta():
    control.makeFile(data_path)
    conn = db.connect(os.path.join(data_path, 'meta.5.db'))
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_providers():
    conn = _get_connection_providers()
    return conn.cursor()

def _get_connection_providers():
    control.makeFile(data_path)
    conn = db.connect(os.path.join(data_path, 'providers.13.db'))
    conn.row_factory = _dict_factory
    return conn

def _get_connection_cursor_search():
    conn = _get_connection_search()
    return conn.cursor()

def _get_connection_search():
    control.makeFile(data_path)
    conn = db.connect(os.path.join(data_path, 'search.1.db'))
    conn.row_factory = _dict_factory
    return conn

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _hash_function(function_instance, *args):
    return _get_function_name(function_instance) + _generate_md5(args)


def _get_function_name(function_instance):
    return re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', repr(function_instance))


def _generate_md5(*args):
    md5_hash = hashlib.md5()
    args = utils.traverse(args)
    [md5_hash.update(six.ensure_binary(arg, errors='replace')) for arg in args]
    return str(md5_hash.hexdigest())


def _is_cache_valid(cached_time, cache_timeout):
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff

