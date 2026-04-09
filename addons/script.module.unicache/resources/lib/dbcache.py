import re
import hashlib
import time
from ast import literal_eval as evaluate
from sqlite3 import dbapi2 as database


MINUTES = 3600


def get(func, duration, path, *args, **table):

    if not path.endswith('.db'):
        return None

    try:

        response = None

        f = repr(func)
        f = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i in args:
            a.update(i.encode('utf-8'))
        a = str(a.hexdigest())

    except Exception:

        pass

    try:
        table = table['table']
    except Exception:
        table = 'rel_list'

    try:

        dbcon = database.connect(path)

        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM {tn} WHERE func = '{f}' AND args = '{a}'".format(tn=table, f=f, a=a))
        match = dbcur.fetchone()

        try:
            response = evaluate(match[2].encode('utf-8'))
        except AttributeError:
            response = evaluate(match[2])

        t1 = float(match[3])
        t2 = time.time()
        update = (abs(t2 - t1) / float(MINUTES)) >= float(duration)
        if not update:
            return response

    except Exception:

        pass

    try:

        r = func(*args)
        if (r is None or r == []) and response is not None:
            return response
        elif r is None or r == []:
            return r

    except Exception:
        return None

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
def timeout(func, path, *args, **table):

    if not path.endswith('.db'):
        return None

    try:

        f = repr(func)
        f = re.sub(r'.+\smethod\s|.+function\s|\sat\s.+|\sof\s.+', '', f)

        a = hashlib.md5()
        for i in args:
            a.update(i.encode('utf-8'))
        a = str(a.hexdigest())
    except Exception:
        pass

    try:
        table = table['table']
    except Exception:
        table = 'rel_list'

    try:

        dbcon = database.connect(path)

        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM {tn} WHERE func = '{f}' AND args = '{a}'".format(tn=table, f=f, a=a))
        match = dbcur.fetchone()
        return int(match[3])

    except Exception:

        return


def clear(path, table=None):

    if not path.endswith('.db'):
        return None

    try:

        if table is None:
            table = ['rel_list', 'rel_lib']
        elif not type(table) == list:
            table = [table]

        dbcon = database.connect(path)
        dbcur = dbcon.cursor()

        for t in table:
            try:
                dbcur.execute("DROP TABLE IF EXISTS {0}".format(t))
                dbcur.execute("VACUUM")
                dbcon.commit()
            except Exception:
                pass

    except Exception:
        pass
