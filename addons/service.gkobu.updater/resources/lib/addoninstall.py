import os, glob, re, xbmcvfs
try:    from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database
from datetime import date, datetime, timedelta

HOME           = xbmcvfs.translatePath('special://home/')
USERDATA       = os.path.join(HOME,      'userdata')
DATABASE       = os.path.join(USERDATA,  'Database')


def addonDatabase(addon=None, state=1, array=False):
    dbfile = latestDB('Addons')
    dbfile = os.path.join(DATABASE, dbfile)
    installedtime = str(datetime.now())[:-7]
    if os.path.exists(dbfile):
        try:
            textdb = database.connect(dbfile)
            textexe = textdb.cursor()
        except Exception as e:
            # log("DB Connection Error: %s" % str(e), xbmc.LOGERROR)
            return False
    else: return False
    if state == 2:
        if array == False:
            try:
                textexe.execute("DELETE FROM installed WHERE addonID = ?", (addon,))
            except Exception as e:
                pass
                # log("Error Removing %s from DB" % addon)
        else:
            for item in addon:
                try:
                    textexe.execute("DELETE FROM installed WHERE addonID = ?", (item,))
                except Exception as e:
                    pass
                    # log("Error Removing %s from DB" % addon)
        textdb.commit()
        textexe.close()
        return True
    try:
        if array == False:
            textexe.execute('INSERT or IGNORE into installed (addonID , enabled, installDate) VALUES (?,?,?)', (addon[0], state, installedtime,))
            textexe.execute('UPDATE installed SET enabled = ?, origin = ? WHERE addonID = ? ', (state, addon[1], addon[0],))
        else:
            for item in addon:
                textexe.execute('INSERT or IGNORE into installed (addonID , enabled, installDate) VALUES (?,?,?)', (item[0], state, installedtime,))
                textexe.execute('UPDATE installed SET enabled = ?, origin = ? WHERE addonID = ? ', (state, item[1], item[0],))
        textdb.commit()
        textexe.close()
    except Exception as e:
        pass
        # log("Erroring enabling addon: %s" % addon)


def latestDB(DB):
    if DB in ['Addons', 'ADSP', 'Epg', 'MyMusic', 'MyVideos', 'Textures', 'TV', 'ViewModes']:
        match = glob.glob(os.path.join(DATABASE,'%s*.db' % DB))
        comp = '%s(.+?).db' % DB[1:]
        highest = 0
        for file in match :
            try: check = int(re.compile(comp).findall(file)[0])
            except: check = 0
            if highest < check :
                highest = check
        return '%s%s.db' % (DB, highest)
    else: return False
