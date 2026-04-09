# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import absolute_import
from kodi_six import xbmc
from tulip import control
from tulip.compat import is_py3

LOGDEBUG = xbmc.LOGDEBUG
LOGERROR = xbmc.LOGERROR
LOGNONE = xbmc.LOGNONE
LOGWARNING = xbmc.LOGWARNING

if is_py3:
    LOGNOTICE = xbmc.LOGWARNING
    LOGSEVERE = xbmc.LOGERROR
    LOGINFO = xbmc.LOGWARNING
    LOGFATAL = xbmc.LOGERROR
else:
    LOGNOTICE = xbmc.LOGNOTICE
    LOGSEVERE = xbmc.LOGSEVERE
    LOGINFO = xbmc.LOGINFO
    LOGFATAL = xbmc.LOGFATAL

def log_debug(msg):
    log(msg, level=LOGDEBUG)


def log_notice(msg):
    log(msg, level=LOGNOTICE)


def log_warning(msg):
    log(msg, level=LOGWARNING)


def log_error(msg):
    log(msg, level=LOGERROR)


def log_info(msg):
    log(msg, level=LOGINFO)


def log_severe(msg):
    log(msg, level=LOGSEVERE)


def log(msg, level=LOGDEBUG, setting=None):
    # override message level to force logging when addon logging turned on

    if level == LOGDEBUG and setting and control.setting(setting) == 'true':
        level = LOGNOTICE

    try:
        xbmc.log('{0}, {1}:: {2}'.format(control.addonInfo('name'), control.addonInfo('version'), msg), level)
    except Exception:
        try:
            xbmc.log('{0}'.format(msg), level)
        except Exception as reason:
            xbmc.log('Logging Failure: {0}' % reason, level)


__all__ = ['log_notice', 'log_debug', 'log_info', 'log_warning', 'log_error']
