import xbmcgui, xbmc, sys, os, time
import zipfile
from resources.lib import monitor

def all(_in, _out, dp=None):
    if dp:
        return allWithProgress(_in, _out, dp)

    return allNoProgress(_in, _out)
        

def allNoProgress(_in, _out):
    try:
        zin = zipfile.ZipFile(_in, 'r')
        zin.extractall(_out)
    except Exception as e:
        print(str(e))
        return False

    return True


def allWithProgress(_in, _out, dp):

    zin = zipfile.ZipFile(_in,  'r')

    nFiles = float(len(zin.infolist()))
    count  = 0

    try:
        for item in zin.infolist():
            file_date_time = item.date_time
            file_date_time = time.mktime(file_date_time + (0, 0, -1))
            if monitor.waitForAbort(0.005):
                dp.close()
                sys.exit()
            count += 1
            update = count / nFiles * 100
            dp.update(int(update))
            extracted_path = zin.extract(item, _out)
            try:
                os.utime(extracted_path, (file_date_time, file_date_time))
            except:
                pass
    except Exception as e:
        print(str(e))
        xbmcgui.Dialog().notification("GKoBu", str(e), xbmcgui.NOTIFICATION_ERROR, 3000, False)
        return False

    return True