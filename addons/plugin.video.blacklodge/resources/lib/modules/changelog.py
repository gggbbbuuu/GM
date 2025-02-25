# -*- coding: utf-8 -*-

import os
from resources.lib.modules import control, log_utils

def get():
    try:
        changelogfile = os.path.join(control.addonPath, 'changelog.txt')
        head = 'Blacklodge  -- Changelog --'
        control.textViewer(file=changelogfile, heading=head)
    except:
        control.infoDialog('Error opening changelog', sound=True)
        log_utils.log('changeloglog_view_fail', 1)

def services_info():
    try:
        services_info_file = os.path.join(control.addonPath, 'resources/text/services.txt')
        head = 'Blacklodge  -- INFO --'
        control.textViewer(file=services_info_file, heading=head)
    except:
        control.infoDialog('Error opening infotext', sound=True)
        log_utils.log('services_info_view_fail', 1)
