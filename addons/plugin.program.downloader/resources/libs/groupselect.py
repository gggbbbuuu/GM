# -*- coding: utf-8 -*-
import xbmc
import sys
import json
import xbmcgui
def getchannelgroups():
    global CHANNELGROUPS, channelgroups, numb
    CHANNELGROUPS = []
    ret = json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "PVR.GetChannelGroups", "params":{"channeltype":"tv"} }'))
    channelgroups = ret['result']['channelgroups']
    for channelgroup in channelgroups:
        chanstring = str(channelgroup)
        try:
            start = "'label': '"
            end = "'}"      
            group = (chanstring.split(start))[1].split(end)[0]
        except:
            continue
        CHANNELGROUPS.append(group)
    numb = len(CHANNELGROUPS)
    c = 0
    while c < numb:
        c = c + 1
    
def setf():
    global a, f
    if a in ["Channels", "channels", "Channel", "channel"]:
        f = 1
        f = int(f)
    elif a in ['Guide', 'guide']:
        f = 2
        f = int(f)
    else:
        f = 1
        f = int(f)

def setg():
    global b, g, CHANNELGROUPS, channelgroups, numb
    c = 0
    g = 0
    while c < numb:
        GRP = CHANNELGROUPS[c]
        if b.lower() in CHANNELGROUPS[c].lower():
            g = c + 1
        c = c + 1

def opengroups():
    global f, g
    if f == 1:
        xbmc.executebuiltin('ActivateWindow(TVChannels)')
    elif f == 2: 
        xbmc.executebuiltin('ActivateWindow(TVGuide)')
    if b == 'last':
        finish()
    c = 2
    xbmc.executebuiltin('SendClick(28)')
    xbmc.executebuiltin( "Action(FirstPage)" )
    if g > 1:
        while (c <= g): 
            c = c + 1
            xbmc.executebuiltin( "Action(Down)" )
    if g >= 1:      
        xbmc.executebuiltin( "Action(Select)" )
        xbmc.executebuiltin( "Action(Right)" )
        xbmc.executebuiltin( "ClearProperty(SideBladeOpen)" )

def finish():
    exit()
yes = xbmcgui.Dialog().yesno("[B][COLOR blue]GKoBu Build Υποστήριξη PVR[/COLOR][/B]", "Μπορείτε να επιλέξετε [B][COLOR yellow]Ελληνικά[/COLOR][/B] για να εμφανιστεί το βασικό γκρουπ Ελληνικών καναλιών. Υπάρχει όμως η πιθανότητα σε ορισμένα portal να υπάρχουν επιμέρους γκρουπ με ελληνικά κανάλια. Η επιλογή αυτών γίνεται μέσω της επιλογής [B][COLOR yellow]Όλα τα γκρουπ[/COLOR][/B][CR]Μπορείτε να επιλέξετε [B][COLOR yellow]Όλα τα γκρουπ[/COLOR][/B] αν θέλετε να διαλέξετε από την συνολική λίστα με τα γκρουπ καναλιών", nolabel='[B][COLOR yellow]Ελληνικά[/COLOR][/B]', yeslabel='[B][COLOR yellow]Όλα τα γκρουπ[/COLOR][/B]')
if yes == False:
    script = sys.argv[0]
    if not xbmc.getCondVisibility('System.HasPVRAddon'):
        xbmc.executebuiltin('Notification(PVR addon, is not enabled)')
        finish()
    if len(sys.argv) > 1:
        a = sys.argv[1]
        b = sys.argv[2]
    else:
        a = 'channels'
        b = sys.argv[1]
    setf()
    getchannelgroups()
    if not b == 'last':
        setg()
    opengroups()
    finish()
else:
    xbmc.executebuiltin('ActivateWindow(TVChannels)')
    xbmc.executebuiltin('SendClick(28)')

