import xbmcgui
import urllib.request, urllib.parse, urllib.error
import time
from urllib.request import FancyURLopener
import sys
from resources.modules import user

class MyOpener(FancyURLopener):
    version = user.name

myopener = MyOpener()
urlretrieve = MyOpener().retrieve
urlopen = MyOpener().open

def download(url, dest, dp = None):
    if not dp:
        dp = xbmcgui.DialogProgress()
        dp.create(' ',"Download In Progress",' ', ' ')
    dp.update(0)
    start_time=time.time()
    urlretrieve(url, dest, lambda nb, bs, fs: _pbhook(nb, bs, fs, dp, start_time))

def auto(url, dest, dp = None):
    dp = xbmcgui.DialogProgress()
    start_time=time.time()
    urlretrieve(url, dest, lambda nb, bs, fs: _pbhookauto(nb, bs, fs, dp, start_time))

def _pbhookauto(numblocks, blocksize, filesize, url, dp):
    none = 0

def _pbhook(numblocks, blocksize, filesize, dp, start_time):
        try: 
            percent = min(numblocks * blocksize * 100 / filesize, 100) 
            currently_downloaded = float(numblocks) * blocksize / (1024 * 1024) 
            kbps_speed = numblocks * blocksize / (time.time() - start_time) 
            if kbps_speed > 0: 
                eta = (filesize - numblocks * blocksize) / kbps_speed 
            else: 
                eta = 0 
            kbps_speed = kbps_speed / 1024 
            mbps_speed = kbps_speed / 1024 
            total = float(filesize) / (1024 * 1024) 
            mbs = '[COLOR white]%.02f MB[/COLOR] of %.02f MB' % (currently_downloaded, total)
            e = 'Speed: [COLOR lime]%.02f Mb/s ' % mbps_speed  + '[/COLOR]'
            e += 'ETA: [COLOR yellow]%02d:%02d' % divmod(eta, 60) + '[/COLOR]'
            dp.update(percent, mbs+'[CR]'+e)
        except: 
            percent = 100 
            dp.update(percent) 
        if dp.iscanceled():
            dialog = xbmcgui.Dialog()
            dialog.ok("Flawless", 'The download was cancelled.')
                
            sys.exit()
            dp.close()