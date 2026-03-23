# -*- coding: utf-8 -*-

import time

try: from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database

from resources.lib.modules import control
from resources.lib.modules import trakt
from resources.lib.modules import log_utils


def get(media_type, imdb, season, episode, local=False):

    if control.setting('rersume.source') == '1' and trakt.getTraktCredentialsInfo() == True and local == False:
        try:
            if media_type == 'episode':

                # Looking for a Episode progress
                traktInfo = trakt.getTrakt('https://api.trakt.tv/sync/playback/episodes?extended=full')
                for i in traktInfo:
                    if imdb == i['show']['ids']['imdb']:
                        # Checking Episode Number
                        if int(season) == i['episode']['season'] and int(episode) == i['episode']['number']:
                            seekable = 1 < i['progress'] < 92
                            if seekable:
                                # Calculating Offset to seconds
                                offset = (float(i['progress'] / 100) * int(i['episode']['runtime']) * 60)
                            else:
                                offset = 0
            else:

                # Looking for a Movie Progress
                traktInfo = trakt.getTrakt('https://api.trakt.tv/sync/playback/movies?extended=full')
                for i in traktInfo:
                    if imdb == i['movie']['ids']['imdb']:
                        seekable = 1 < i['progress'] < 92
                        if seekable:
                            # Calculating Offset to seconds
                            offset = (float(i['progress'] / 100) * int(i['movie']['runtime']) * 60)
                        else:
                            offset = 0

            return offset

        except:
            return 0

    else:
        try:
            sql_select = "SELECT * FROM bookmarks WHERE imdb = '%s'" % imdb
            if media_type == 'episode':
                sql_select += " AND season = '%s' AND episode = '%s'" % (season, episode)

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.bookmarksFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS bookmarks (""played_seconds INTEGER, ""type TEXT, ""imdb TEXT, ""meta TEXT, ""season TEXT, ""episode TEXT, ""playcount INTEGER, ""overlay INTEGER, ""progress INTEGER, ""time INTEGER, ""UNIQUE(imdb, season, episode)"");")
            dbcur.execute(sql_select)
            match = dbcur.fetchone()
            dbcon.commit()
            if match:
                return int(match[0])
            else:
                return 0
        except:
            log_utils.log('bookmarks_get', 1)
            return 0

    return 0


def reset(current_time, total_time, media_type, imdb, meta, season='', episode=''):
    try:
        t = int(time.time())
        playcount = 0
        overlay = 6
        played_seconds = int(current_time)
        progress = int((played_seconds / total_time) * 100)
        ok = int(played_seconds) > 120 and progress < 92
        watched = progress >= 92

        sql_select = "SELECT * FROM bookmarks WHERE imdb = '%s' AND season = '%s' AND episode = '%s'" % (imdb, season, episode)

        sql_update = "UPDATE bookmarks SET played_seconds = %s, progress = %s, time = %s WHERE imdb = '%s' AND season = '%s' AND episode = '%s'" % (played_seconds, progress, t, imdb, season, episode)

        sql_update_watched = "UPDATE bookmarks SET played_seconds = 0, playcount = %s, overlay = %s, progress = %s, time = %s WHERE imdb = '%s' AND season = '%s' AND episode = '%s'" % ('%s', '%s', progress, t, imdb, season, episode)

        control.makeFile(control.dataPath)
        dbcon = database.connect(control.bookmarksFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS bookmarks (""played_seconds INTEGER, ""type TEXT, ""imdb TEXT, ""meta TEXT, ""season TEXT, ""episode TEXT, ""playcount INTEGER, ""overlay INTEGER, ""progress INTEGER, ""time INTEGER, ""UNIQUE(imdb, season, episode)"");")
        dbcur.execute(sql_select)
        match = dbcur.fetchone()
        if match:
            if ok:
                dbcur.execute(sql_update)
            elif watched:
                playcount = match[6] + 1
                overlay = 7
                dbcur.execute(sql_update_watched % (playcount, overlay))
        else:
            if watched:
                playcount = 1
                overlay = 7
            dbcur.execute("INSERT INTO bookmarks Values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (played_seconds, media_type, imdb, meta, season, episode, playcount, overlay, progress, t))
        dbcon.commit()
    except:
        log_utils.log('bookmarks_reset', 1)
        pass


def set_scrobble(current_time, total_time, _content, _imdb='', _season='', _episode=''):
    try:
        if not (current_time == 0 or total_time == 0):
            percent = float((current_time / total_time)) * 100
        else:
            percent = 0
        if _content == 'movie':
            if int(current_time) > 120 and 2 < percent < 92:
                trakt.scrobbleMovie(_imdb, percent, action='pause')
                if control.setting('trakt.scrobble.notify') == 'true':
                    control.sleep(1000)
                    control.infoDialog('Trakt: Scrobble Paused')
            elif percent >= 92:
                trakt.scrobbleMovie(_imdb, percent, action='stop')
                if control.setting('trakt.scrobble.notify') == 'true':
                    control.sleep(1000)
                    control.infoDialog('Trakt: Scrobbled')
        else:
            if int(current_time) > 120 and 2 < percent < 92:
                trakt.scrobbleEpisode(_imdb, _season, _episode, percent, action='pause')
                if control.setting('trakt.scrobble.notify') == 'true':
                    control.sleep(1000)
                    control.infoDialog('Trakt: Scrobble Paused')
            elif percent >= 92:
                trakt.scrobbleEpisode(_imdb, _season, _episode, percent, action='stop')
                if control.setting('trakt.scrobble.notify') == 'true':
                    control.sleep(1000)
                    control.infoDialog('Trakt: Scrobbled')
    except:
        log_utils.log('Scrobble - Exception', 1)
        control.infoDialog('Scrobble Failed')


def _indicators(media_type):
    sql_select = "SELECT * FROM bookmarks WHERE type = '%s' AND overlay = 7" % media_type
    control.makeFile(control.dataPath)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute("CREATE TABLE IF NOT EXISTS bookmarks (""played_seconds INTEGER, ""type TEXT, ""imdb TEXT, ""meta TEXT, ""season TEXT, ""episode TEXT, ""playcount INTEGER, ""overlay INTEGER, ""progress INTEGER, ""time INTEGER, ""UNIQUE(imdb, season, episode)"");")
    dbcur.execute(sql_select)
    match = dbcur.fetchall()
    dbcon.commit()
    if match:
        return match
    return []


def _get_watched(media_type, imdb, season, episode):
    sql_select = "SELECT * FROM bookmarks WHERE imdb = '%s' AND overlay = 7" % imdb
    if media_type == 'episode':
        sql_select += " AND season = '%s' AND episode = '%s'" % (season, episode)
    control.makeFile(control.dataPath)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute(sql_select)
    match = dbcur.fetchone()
    dbcon.commit()
    if match:
        return 7
    else:
        return 6


def _update_watched(new_value, imdb, season, episode):
    sql_update = "UPDATE bookmarks SET overlay = %s" % new_value
    if new_value < 7:
        sql_update += ", playcount = 0"
    sql_update += " WHERE imdb = '%s' AND season = '%s' AND episode = '%s'" % (imdb, season, episode)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute(sql_update)
    dbcon.commit()


def _delete_record(imdb, season, episode):
    sql_delete = "DELETE FROM bookmarks WHERE imdb = '%s' AND season = '%s' AND episode = '%s'" % (imdb, season, episode)
    dbcon = database.connect(control.bookmarksFile)
    dbcur = dbcon.cursor()
    dbcur.execute(sql_delete)
    dbcon.commit()


