# -*- coding: utf-8 -*-
import re
import os
import xbmcvfs, xbmc

def openfile(path_to_the_file):
    try:
        fh = xbmcvfs.File(path_to_the_file)
        contents=fh.read()
        fh.close()
        return contents
    except:
        print("Wont open: %s" % path_to_the_file)
        return None

def savefile(path_to_the_file,content):
    try:
        fh = xbmcvfs.File(path_to_the_file, 'w')
        fh.write(content)  
        fh.close()
    except: print("Wont save: %s" % path_to_the_file)


_rooterFile = os.path.join(xbmcvfs.translatePath('special://home/addons/plugin.video.seren'), 'resources', 'lib', 'modules', 'router.py')
if os.path.exists(_rooterFile):
        data = openfile(_rooterFile)
        if not 'http://bit.ly/a4kScrapers' in data:
            oldaction = 'ProviderInstallManager().install_package(1, url=url)'
            newaction = 'ProviderInstallManager().install_package(1, url="http://bit.ly/a4kScrapers")'
            new_data = data.replace(oldaction, newaction)
            savefile(_rooterFile,new_data)
            xbmc.sleep(1000)
        else:
            pass
        xbmc.executebuiltin('RunPlugin(plugin://plugin.video.seren/?action=externalProviderInstall)')
else:
    pass
