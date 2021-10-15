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

exec("import re;import base64");exec((lambda p,y:(lambda o,b,f:re.sub(o,b,f.decode('utf-8')))(r"([0-9a-f]+)",lambda m:p(m,y),base64.b64decode("MzgoIjYgNGQ7NiAxNSIpOzM4KCgzIDhiLDkwOigzIDllLGIsZjo0ZC44MSg5ZSxiLGYuMTQoJzRiLTgnKSkpKGExIihbMC05YS1mXSspIiwzIDk1OjhiKDk1LDkwKSwxNS4yYygiOGQvNC8yLzk2PSIpKSkoMyBhLGI6Yls4YSgiOWMiK2EuNWQoMSksMTYpXSwiMHwxfDd8NmZ8MWZ8MTh8OTF8MTd8OHw5ZHw0NHwzMnwyZnw5ZnwyZHxmfDEwfDQ4fDQ5fDJhfDFifDM1fDZifDEyfDEzfDI4fDI5fDV8MWF8MzZ8Mzd8NWV8ZHw3NnwxOXw5MnwxY3wzZHw0MXw0N3wyMnwyMXw1Y3wyYnw0ZXwyZXw4OXw2fDMwfDMxfDhlfDMzfDM0fDY2fDZhfDc1fDM5fDNhfDNifDNmfGN8NDV8ZXwxMXw4Mnw0Znw3M3w5OXw1Mnw4OHwxZHwxZXwyMHw1NXw5NHw1Nnw1OHw1Ynw2MnwyNnwyN3w4N3w2OHw3ZHw2ZXw2Y3w2ZHw5N3w3NHw3OHw4MHwzY3wzZXw0MHw0Mnw0M3w0Nnw0YXw4NHw4M3w0Y3w4Znw4Nnw5OHwxNHw1MHw1MXw5Ynw1M3w1NHw1OXw1YXw1Znw2MXw2MHw2NHw2NXw5fDY3fDY5fDRkfDcwfDIzfDcyfDdjfDc3fDc5fDdhfDdifDYzfDdlfDdmfDg1fDRifDhjfDkzfGEwfGEyfGEzfDI1fDcxfDI0Ii41NygifCIpKSk=")))(lambda a,b:b[int("0x"+a.group(1),16)],"0|1|PiguKz8pPDU0PicsICczNS02Yz0iKFteIl0rKS4rPzM1LTNiPSIoW14iXSspLis|lambda|MzVcLTNiPSIoW14iXSspLis|busydialognocancel|import|addon_EntertainMe|8|path_to_the_file|a|b|AddonIsEnabled|contextmanager|ActivateWindow|f|10|BaseException|translatePath|addon_fmovies|decode|base64|16|getAddonInfo|basecontent|EntertainMe|fmovies_ver|okpnfmovies|busy_dialog|updatecheck|repository|newcontent|contextlib|nemesisaio|downloader|getSetting|basepypath|setSetting|addonname|gknwizard|enter_ver|okpnenter|xbmcaddon|pinstatus|b64decode|addonPath|jfilename|addonbase|resources|fmoviesto|addonInfo|savefile|contents|neme_ver|okpnneme|openfile|exec|requests|jsondata|fixpath|nemesis|version|xbmcgui|servers|timeout|replace|findall|special|xbmcvfs|program|finally|content|action|plugin|System|utf|Dialog|re|except|Passed|Builds|addons|return|number|yield|close|print|split|sleep|Close|gkobu|write|Addon|group|video|fixen|loads|GKoBu|match|read|save|http|data|repo|elif|copy|None|xbmc|with|pass|span|executebuiltin|home|fix_enter_ver|name|join|else|File|path|load|open|okpn|from|main|argv|json|xmls|libs|Wont|sub|pin|300|sys|get|str|not|try|def|int|p|eu|MmYgMTYsMTMsYSw1YwoyZiA1NywgNzgsIDM4LCA2Mgo3ZiA0OCAyZiAyMAoKMTEgPSA2Mi43Y1sxXQpjID0gMTMuMmEoJzEyLjNkLjI4JykKOSA9IDEzLjJhKCcxMi4xZi4yOScpCjIgPSAxMy4yYSgnMTIuMWYuMjInKQoxOCA9IDEzLjJhKCcxMi4xZi4zMScpCmQgPSBjLjdhKCcxZCcpCjIzIGQgPT0gJycgNjcgZCA2NSAzNjoKCWQgPSAnMCcKOGMgPSBjLjdhKCcxYScpCjIzIDhjID09ICcnIDY3IDhjIDY1IDM2OgoJOGMgPSAnMCcKNiA9IGMuN2EoJzE0JykKMjMgNiA9PSAnJyA2NyA2IDY1IDM2OgoJNiA9ICcwJwoxNSA9IDkuNygnMjUnKQoxOSA9IDIuNygnMjUnKQoxYyA9IDE4LjcoJzI1JykKCgpAMjAKMmUgMjQoKToKCTE2LjMoJzNlKDFiKScpCgk0NToKCQk2ZAoJNjA6CgkJMTYuMygnNjQuNmUoMWIpJykKCjJlIDFlKDc1KToKCTQ1OgoJCTQzID0gYS4zNyg3NSkKCQkzND00My44MSgpCgkJNDMuNDkoKQoJCTQ0IDM0CgkyYzoKCQk0YigiNWEgNTk6ICU4OSIgJSA3NSkKCQk0NCAzNgoKMmUgMzMoNzUsMjcpOgoJNDU6CgkJNDMgPSBhLjM3KDc1LCAnOGEnKQoJCTQzLjRkKDI3KSAgCgkJNDMuNDkoKQoJMmM6IDRiKCI1YSA3MzogJTg5IiAlIDc1KQoKMmUgMWQoKToKCTU1IDI0KCk6CgkJMjMgZCA8IDE1OgoJCQliID0gOS43CgkJCWUgPSBhLjE3KGIoJzIxJykpCgkJCThkID0gNTcuMjEuNDIoZSwnNWIuNmInKQoJCQk0ZiA9IGIoJzdiJykKCQkJMmIgPSA5LjdhKCc0MCcpCgkJCTUgPSAxZSg4ZCkKCQkJMjMgNTEgMTUgNGEgNToKCQkJCTQ1OgoJCQkJCTQgPSAzOC44NCgnNzQ6Ly81MC44Ni83Ni82OS83MS84Mi83ZScsIDVkPTEwKS4yNwoJCQkJCTQgPSA0LjY4KCc4NS04JykKCQkJCQk0ZSA9IDc4LjVlKCcjIyguKz8pIyMnLCA0KVswXQoJCQkJCTIzIDUxIDY2KDRlKSA8IDY2KDE1KToKCQkJCQkJMzMoOGQsNCkKCQkJCQkJMTYuNGMoNjMpCgkJCQkJCTkuOGIoJzQwJywgJzQxJykKCQkJCQkJYy44YignMWQnLCAxNSkKCQkJCTJjIDNmOgoJCQkJCTU2CgoJMTYuMygxMSkKCgoyZSAxYSgpOgoJMjMgOGMgPCAxOToKCQliID0gMi43CgkJZSA9IGEuMTcoYignMjEnKSkKCQk4ZCA9IDU3LjIxLjQyKGUsJzMwJywgJzgzJywgJzQ2LjZiJykKCQkzYSA9ICc1ZjovLzc5LzZhLzEyLjNkLjI4LzMwLzcwJwoJCTJiID0gMi43YSgnNDAnKQoJCTUgPSAxZSg4ZCkKCQkyMyA1MSAxOSA0YSA1OgoJCQlhLjc3KDNhLCA4ZCkKCQkJMTYuNGMoNjMpCgkJCTIuOGIoJzQwJywgJzQxJykKCQkJYy44YignMWEnLCAxOSkKCgkxNi4zKDExKQoKMmUgMTQoKToKCSMgMjMgNiA8IDFjOgoJYiA9IDE4LjcKCWUgPSBhLjE3KGIoJzIxJykpCgk4ZCA9IDU3LjIxLjQyKGUsJzgwLjZiJykKCTUgPSAxZSg4ZCkKCSMgNCA9IDUuMjYoJzU5KDJkKScsICdhLjM3KDJkKScpLjI2KCczOSA9IDUzLjcyKGYpJywgJzM5ID0gNTMuN2QoZiknKQoJNCA9IDUuMjYoJzM1LTg3PSIoW14iXSspLis|getCondVisibility|is|y|fix_fmovies_ver|if|id|in|m|PiguKz8pPDU0PicpCgk1NSBhLjM3KDhkLCAnOGEnKSA4OCBmOgoJCWYuNGQoNCkKCWMuOGIoJzE0JywgMWMpCgoJMTYuMygxMSkKCjIzIDE2LjMyKCc2MS4zYyg0Ny42ZiknKToKCTIzICcxMi4xZi4yOScgNGEgMTE6CgkJMWQoKQoJNTIgJzEyLjFmLjIyJyA0YSAxMToKCQkxYSgpCgk1MiAnMTIuMWYuMzEnIDRhIDExOgoJCTE0KCkKCTU4OgoJCTE2LjMoMTEpCjU4OgoJNTY|os|or|fh|9a|py|0x|addon_nemesis|o|fix_neme_ver|as|r|s|w".split("|")))