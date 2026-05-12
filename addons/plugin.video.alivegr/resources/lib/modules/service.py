# -*- coding: utf-8 -*-

# AliveGR Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

import xbmc
import xbmcaddon

__addon_id__ = 'plugin.video.alivegr'


class AliveGRService(xbmc.Monitor):

    def __init__(self):

        super(AliveGRService, self).__init__()
        self.addon = xbmcaddon.Addon(__addon_id__)
        self.auto_start = self.addon.getSetting('auto_start') == 'true'

        if self.auto_start:
            self.launch_logic()

    def onSettingsChanged(self):

        new_val = self.addon.getSetting('auto_start') == 'true'

        if new_val and not self.auto_start:
            self.launch_logic()

        self.auto_start = new_val

        if __addon_id__ in xbmc.getInfoLabel('Container.PluginName'):
            xbmc.executebuiltin('Container.Refresh')

    def launch_logic(self):

        retries = 0
        while not xbmc.getCondVisibility('Window.IsActive(home)') and not self.abortRequested():
            if retries > 60: break
            xbmc.sleep(500)
            retries += 1

        xbmc.executebuiltin(f'RunAddon({__addon_id__})')


if __name__ == '__main__':

    monitor = AliveGRService()

    while not monitor.abortRequested():
        if monitor.waitForAbort(10):
            break
