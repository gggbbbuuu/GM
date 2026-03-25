# -*- coding: utf-8 -*-

import os
import traceback
from datetime import datetime
from kodi_six import xbmc

import six

from io import open

from blackscrapers.modules import control

LOGDEBUG = xbmc.LOGDEBUG
# LOGINFO = xbmc.LOGINFO
# LOGNOTICE = xbmc.LOGNOTICE if control.getKodiVersion() < 19 else xbmc.LOGINFO
# LOGWARNING = xbmc.LOGWARNING
# LOGERROR = xbmc.LOGERROR
# LOGFATAL = xbmc.LOGFATAL
# LOGNONE = xbmc.LOGNONE

name = control.addonInfo('name')
version = control.addonInfo('version')
DEBUGPREFIX = '[ {0} {1} | DEBUG ]'.format(name, version)
INFOPREFIX = '[ %s | INFO ]' % name
LOGPATH = control.transPath('special://logpath/')
log_file = os.path.join(LOGPATH, 'blacklodge.log')
debug_enabled = control.addon('plugin.video.blacklodge').getSetting('addon.debug')


def log(msg, trace=None):

    if not debug_enabled == 'true':
        return

    try:
        if not isinstance(msg, six.string_types):
            msg = repr(msg)
        if trace:
            head = DEBUGPREFIX
            failure = six.ensure_str(traceback.format_exc(), errors='replace')
            _msg = ' %s:\n  %s' % (msg, failure)
        else:
            head = INFOPREFIX
            _msg = '\n    %s' % msg

        #if not debug_log == '0':
        if not os.path.exists(log_file):
            f = open(log_file, 'w')
            f.close()
        with open(log_file, 'a', encoding='utf-8') as f:
            line = '[%s %s] %s%s' % (datetime.now().date(), str(datetime.now().time())[:8], head, _msg)
            f.write(line.rstrip('\r\n')+'\n\n')
        #else:
            #xbmc.log('%s: %s' % (head, _msg), LOGDEBUG)
    except Exception as e:
        try:
            xbmc.log('%s Logging Failure: %s' % (name, e), LOGDEBUG)
        except:
            pass

