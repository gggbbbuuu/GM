import xbmc, xbmcgui, xbmcvfs, xbmcaddon, os, json, sys, re, glob, shutil
try:    from sqlite3 import dbapi2 as database
except: from pysqlite2 import dbapi2 as database
from datetime import datetime
transPath  = xbmcvfs.translatePath
HOME = transPath('special://home/')
ADDONS = os.path.join(HOME, 'addons')
USERDATA       = os.path.join(HOME, 'userdata')
ADDONDATA      = os.path.join(USERDATA, 'addon_data')
DATABASE       = os.path.join(USERDATA, 'Database')
add_on = xbmcaddon.Addon()
addon_id = add_on.getAddonInfo('id')
addontitle = add_on.getAddonInfo('name')
lang = add_on.getLocalizedString
dp = xbmcgui.DialogProgress()
SYSTEM_ADDONS =    ["game.controller.default",
                    "game.controller.snes",
                    "inputstream.adaptive",
                    "metadata.album.universal",
                    "metadata.artists.universal",
                    "metadata.common.imdb.com",
                    "metadata.common.themoviedb.org",
                    "metadata.themoviedb.org.python",
                    "metadata.tvshows.themoviedb.org",
                    "metadata.tvshows.themoviedb.org.python",
                    "service.xbmc.versioncheck"]
def removeaddon():
    dirs, files = xbmcvfs.listdir(ADDONS)
    modes = [lang(30001), lang(30002)]
    datamodes = [lang(30003), lang(30004)]
    selectmode = xbmcgui.Dialog().select(lang(30005), modes)
    if selectmode == -1: sys.exit()
    selectdatamode = xbmcgui.Dialog().select(lang(30006), datamodes)
    if selectdatamode == -1: sys.exit()
    query = '{ "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails", "params": { "addonid": "%s", "properties" : ["name", "path", "thumbnail", "dependencies"] } }'
    addonsinfo = []
    for folder in dirs:
        if folder == "packages":
            continue
        if folder == "temp":
            continue
        if folder in SYSTEM_ADDONS:
            continue
        addonDetails = xbmc.executeJSONRPC(query  % folder)
        details_result = json.loads(addonDetails)
        if "error" in details_result:
            continue
        addonid = details_result['result']['addon']['addonid']
        addonname = re.sub("[\[].*?[\]]", "", details_result['result']['addon']['name'])
        addonname = re.sub("^\s+", "", addonname)
        addondeps = details_result['result']['addon']['dependencies']
        addoninfo = [addonid, addonname, addondeps]
        addonsinfo.append(addoninfo)
    addonsinfo.sort(key=lambda x: x[1])
    addonslistrange = list(range(len(addonsinfo)))
    selected = xbmcgui.Dialog().multiselect(lang(30007), [el[1] for el in addonsinfo])
    if selected == None: sys.exit()
    if len(selected) > 0:
        remainaddons = [x for x in addonslistrange if x not in selected]
        idsTOremove = []
        idsTOremove1 = []
        idsTOremain = []
        for addon in selected:
            idsTOremove.append(addonsinfo[addon][0])
            idsTOremove1.append(addonsinfo[addon][0])
            deps = addonsinfo[addon][2]
            depids = []
            for dep in deps:
                depid = dep.get('addonid')
                depids.append(depid)
                idsTOremove.extend(depids)
            aadeps = []
            for depdep in depids:
                depaddonDetails = xbmc.executeJSONRPC(query  % depdep)
                depdetails_result = json.loads(depaddonDetails)
                if "error" in depdetails_result:
                    continue
                depaddonid = depdetails_result['result']['addon']['addonid']
                depaddonname = depdetails_result['result']['addon']['name']
                depaddondeps = depdetails_result['result']['addon']['dependencies']
                depaddoninfo = [depaddonid, depaddonname, depaddondeps]
                for dep in depaddoninfo[2]:
                    aa = dep.get("addonid")
                    aadeps.append(aa)
            idsTOremove.extend(aadeps)
        idsTOremove = list(dict.fromkeys(idsTOremove))
        for raddon in remainaddons:
            idsTOremain.append(addonsinfo[raddon][0])
            rdeps = addonsinfo[raddon][2]
            rdepids = []
            for rdep in rdeps:
                rdepid = rdep.get('addonid')
                rdepids.append(rdepid)
                idsTOremain.extend(rdepids)
            raadeps = []
            for rdepdep in rdepids:
                rdepaddonDetails = xbmc.executeJSONRPC(query  % rdepdep)
                rdepdetails_result = json.loads(rdepaddonDetails)
                if "error" in rdepdetails_result:
                    continue
                rdepaddonid = rdepdetails_result['result']['addon']['addonid']
                rdepaddonname = rdepdetails_result['result']['addon']['name']
                rdepaddondeps = rdepdetails_result['result']['addon']['dependencies']
                rdepaddoninfo = [rdepaddonid, rdepaddonname, rdepaddondeps]
                for rdep in rdepaddoninfo[2]:
                    raa = rdep.get("addonid")
                    raadeps.append(raa)
            idsTOremain.extend(raadeps)
        if selectmode == 0: idsfiltered = [x for x in idsTOremove if idsTOremain.count(x) <= 1 and x in dirs and x not in SYSTEM_ADDONS]
        else: idsfiltered = idsTOremove1
        
        if len(idsfiltered) > 0:
            if selectmode == 0:
                xbmcgui.Dialog().ok(addontitle, lang(30008))
                selected2 = xbmcgui.Dialog().multiselect(lang(30009), idsfiltered, preselect=list(range(len(idsfiltered))))
            else:
                selected2 = list(range(len(idsfiltered)))
            finallyremove = []
            if selected2 == None: sys.exit()
            if len(selected2) > 0:
                for ad in selected2:
                    finallyremove.append(idsfiltered[ad])
                total = len(finallyremove)
                step = int(100/total)
                start = 0
                dp.create(addontitle, lang(30010))
                for removeid in finallyremove:
                    start += 1
                    perc = int((start*step)-(2*step/3))
                    perc2 = int((start*step)-(step/3))
                    perc3 = start*step
                    try:
                        addonfolderpath = os.path.join(ADDONS, removeid)
                        addondatapath = os.path.join(ADDONDATA, removeid)
                        if os.path.exists(addonfolderpath):
                            dp.update(perc, lang(30011) % removeid)
                            shutil.rmtree(addonfolderpath)
                            xbmc.sleep(1000)
                            dp.update(perc2, lang(30012) % removeid)
                            addonDatabaseremove(removeid, False)
                            xbmc.sleep(1000)
                            if os.path.exists(addondatapath) and selectdatamode == 0:
                                dp.update(perc3, lang(30013) % removeid)
                                shutil.rmtree(addondatapath)
                                xbmc.sleep(1000)
                    except BaseException:
                        xbmcgui.Dialog().notification(addontitle, lang(30014) % removeid, xbmcgui.NOTIFICATION_INFO, 1000, False)
                        continue
                dp.close()
                xbmc.executebuiltin('UpdateLocalAddons()')
                xbmcgui.Dialog().ok(addontitle, lang(30015))
            else:
                xbmcgui.Dialog().ok(addontitle, lang(30016))
                sys.exit()
        else:
            xbmcgui.Dialog().ok(addontitle, lang(30017))
            sys.exit()

def addonDatabaseremove(addon=None, array=False):
    dbfile = latestDB('Addons')
    dbfile = os.path.join(DATABASE, dbfile)
    installedtime = str(datetime.now())[:-7]
    if os.path.exists(dbfile):
        try:
            textdb = database.connect(dbfile)
            textexe = textdb.cursor()
        except Exception as e:
            return False
    else: return False
    if array == False:
        try:
            textexe.execute("DELETE FROM installed WHERE addonID = ?", (addon,))
        except Exception as e:
            pass
    else:
        for item in addon:
            try:
                textexe.execute("DELETE FROM installed WHERE addonID = ?", (item,))
            except Exception as e:
                pass
    textdb.commit()
    textexe.close()
    return True

def latestDB(DB):
    if DB in ['Addons', 'ADSP', 'Epg', 'MyMusic', 'MyVideos', 'Textures', 'TV', 'ViewModes']:
        match = glob.glob(os.path.join(DATABASE,'%s*.db' % DB))
        comp = '%s(.+?).db' % DB[1:]
        highest = 0
        for file in match :
            try: check = int(re.compile(comp).findall(file)[0])
            except: check = 0
            if highest < check :
                highest = check
        return '%s%s.db' % (DB, highest)
    else: return False

if __name__ == '__main__':
    removeaddon()
