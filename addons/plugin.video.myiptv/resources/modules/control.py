# -*- coding: utf-8 -*-

import os
import sys
import traceback

import six
from six.moves import urllib_parse
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs


def six_encode(txt, char='utf-8', errors='replace'):
    if six.PY2 and isinstance(txt, six.text_type):
        txt = txt.encode(char, errors=errors)
    return txt


def six_decode(txt, char='utf-8', errors='replace'):
    if six.PY3 and isinstance(txt, six.binary_type):
        txt = txt.decode(char, errors=errors)
    return txt


def getKodiVersion():
    return int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])


addon = xbmcaddon.Addon
addonInfo = xbmcaddon.Addon().getAddonInfo

lang = xbmcaddon.Addon().getLocalizedString
lang2 = xbmc.getLocalizedString

setting = xbmcaddon.Addon().getSetting
setSetting = xbmcaddon.Addon().setSetting

addItem = xbmcplugin.addDirectoryItem
addItems = xbmcplugin.addDirectoryItems

item = xbmcgui.ListItem
directory = xbmcplugin.endOfDirectory

content = xbmcplugin.setContent
property = xbmcplugin.setProperty

infoLabel = xbmc.getInfoLabel

condVisibility = xbmc.getCondVisibility

jsonrpc = xbmc.executeJSONRPC

dialog = xbmcgui.Dialog()
progressDialog = xbmcgui.DialogProgress()
progressDialogBG = xbmcgui.DialogProgressBG()
window = xbmcgui.Window(10000)
windowDialog = xbmcgui.WindowDialog()

button = xbmcgui.ControlButton

image = xbmcgui.ControlImage

getCurrentDialogId = xbmcgui.getCurrentWindowDialogId()
getCurrentWinId = xbmcgui.getCurrentWindowId()

keyboard = xbmc.Keyboard

monitor = xbmc.Monitor()

execute = xbmc.executebuiltin

skin = xbmc.getSkinDir()

player = xbmc.Player()
playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
resolve = xbmcplugin.setResolvedUrl

legalFilename = xbmc.makeLegalFilename if getKodiVersion() < 19 else xbmcvfs.makeLegalFilename

openFile = xbmcvfs.File
makeFile = xbmcvfs.mkdir
deleteFile = xbmcvfs.delete

deleteDir = xbmcvfs.rmdir
listDir = xbmcvfs.listdir

transPath = xbmc.translatePath if getKodiVersion() < 19 else xbmcvfs.translatePath
addonPath = transPath(addonInfo('path'))
dataPath = transPath(addonInfo('profile'))
skinPath = transPath('special://skin/')

artPath = os.path.join(addonPath, 'resources', 'images')

settingsPath = os.path.join(addonPath, 'resources', 'settings.xml')
settingsFile = os.path.join(dataPath, 'settings.xml')
cacheFile = os.path.join(dataPath, 'cache.db')


def sleep(time):
    while time > 0 and not monitor.abortRequested():
        xbmc.sleep(min(100, time))
        time = time - 100


def addonId():
    return addonInfo('id')


def addonName():
    return addonInfo('name')


def addonIcon():
    return addonInfo('icon')


def addonFanart():
    if setting('addon.fanart') == 'true':
        return os.path.join(artPath, 'fanart2.jpg')
    else:
        return addonInfo('fanart')


def getCurrentViewId():
    win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    return str(win.getFocusId())


def idle():
    if getKodiVersion() >= 18:
        return execute('Dialog.Close(busydialognocancel)')
    else:
        return execute('Dialog.Close(busydialog)')


def busy():
    if getKodiVersion() >= 18:
        return execute('ActivateWindow(busydialognocancel)')
    else:
        return execute('ActivateWindow(busydialog)')


def refresh():
    return execute('Container.Refresh')


def queueItem():
    return execute('Action(Queue)')


def yesnoDialog(message, heading=addonInfo('name'), nolabel='', yeslabel=''):
    if getKodiVersion() < 19:
        return dialog.yesno(heading, message, '', '', nolabel, yeslabel)
    else:
        return dialog.yesno(heading, message, nolabel, yeslabel)


def okDialog(message, heading=addonInfo('name')):
    return dialog.ok(heading, message)


def selectDialog(list, heading=addonInfo('name'), useDetails=False):
    if getKodiVersion() >= 17:
        return dialog.select(heading, list, useDetails=useDetails)
    else:
        return dialog.select(heading, list)


def infoDialog(message, heading=addonInfo('name'), icon='', time=3000, sound=False):
    if icon == '':
        icon = addonIcon()
    elif icon == 'INFO':
        icon = xbmcgui.NOTIFICATION_INFO
    elif icon == 'WARNING':
        icon = xbmcgui.NOTIFICATION_WARNING
    elif icon == 'ERROR':
        icon = xbmcgui.NOTIFICATION_ERROR
    dialog.notification(heading, message, icon, time, sound=sound)


def textViewer(file, heading=addonInfo('name'), monofont=True):
    sleep(200)
    if not os.path.exists(file):
        w = open(file, 'w')
        w.close()
    with open(file, 'rb') as r:
        text = r.read()
    if not text:
        text = ' '
    head = '[COLOR purple][B]%s[/B][/COLOR]' % six.ensure_str(heading, errors='replace')
    if getKodiVersion() >= 18:
        return dialog.textviewer(head, text, monofont)
    else:
        return dialog.textviewer(head, text)


def openSettings(query=None, id=None):
    try:
        id = addonInfo('id') if id == None else id
        idle()
        execute('Addon.OpenSettings(%s)' % id)
        if query == None:
            raise Exception()
        c, f = query.split('.')
        if getKodiVersion() >= 18:
            execute('SetFocus(%i)' % (int(c) - 100))
            execute('SetFocus(%i)' % (int(f) - 80))
        else:
            execute('SetFocus(%i)' % (int(c) + 100))
            execute('SetFocus(%i)' % (int(f) + 200))
    except:
        return


def metadataClean(metadata):
    if metadata == None:
        return metadata
    allowed = ['aired', 'album', 'artist', 'cast',
        'castandrole', 'code', 'country', 'credits', 'dateadded', 'dbid', 'director',
        'duration', 'episode', 'episodeguide', 'genre', 'imdbnumber', 'lastplayed',
        'mediatype', 'mpaa', 'originaltitle', 'overlay', 'path', 'playcount', 'plot',
        'plotoutline', 'premiered', 'rating', 'season', 'set', 'setid', 'setoverview',
        'showlink', 'sortepisode', 'sortseason', 'sorttitle', 'status', 'studio', 'tag',
        'tagline', 'title', 'top250', 'totalepisodes', 'totalteasons', 'tracknumber',
        'trailer', 'tvshowtitle', 'userrating', 'votes', 'watched', 'writer', 'year'
    ]
    return {k: v for k, v in six.iteritems(metadata) if k in allowed}


