# -*- coding: utf-8 -*-
import xbmc, xbmcaddon, xbmcgui, xbmcvfs, os, sys
from resources.lib import notify, monitor


transPath  = xbmcvfs.translatePath
logo = transPath('special://home/addons/plugin.video.youtube/icon.png')

def setYoutubeSettings():
    try:
        import random
        addons_folder = transPath('special://home/addons/')
        data_folder = transPath('special://home/userdata/addon_data/')
        badapis =          ['AIzaSyA8k1OyLGf03HBNl0byD511jr9cFWo2GR4', 'AIzaSyA2UCDoxiOOXf__8c5PPRFmzBKtq5Nst1c',
                            '', 'AIzaSyDIwGxYCM4WtKM57YbPQPr9Wn8zoaLA4CE',
                            'AIzaSyCTkbjYgtcqaNWkVhLpA7ntA2ZX7uOdCZs', 'AIzaSyDg2R1Md8TpVq111nF3iz-Sh959a0ZcrHI',
                            'AIzaSyBwv7QLg26_I-kg6a40fgXNETjnvLtdxbw', 'AIzaSyAHUXitAhd5MNrfmH8HnPCN7jNtPCcjq70',
                            'AIzaSyBMrqsiBv1F34-AWJCuuB5chuCR6BoYF-8', 'AIzaSyD4_ufoAvDEW4NIkhJyU3RztHVa335klMw',
                            'AIzaSyB2vSwWeoIcX-HTfoj0xAnGgJsOgv_lB90', 'AIzaSyCCbFSPuI925NX2tc7mfGZktm5rKV9_AlE',
                            'AIzaSyAb_T7U2Fn-n8FDr4R0ZvCRj-ysV37p02I', 'AIzaSyA1cpRV2BATmPlguG9cJ8ia3dp5m-dnUqU',
                            'AIzaSyDfGlH2U8YeNCcEgqmBgaNWLm4BItKNX4A', 'AIzaSyAOnpnStrart4pjpO7wBdVXbqUmbocmhXE',
                            'AIzaSyCNEdn9h187ymAJ-s9lfQz-1nNp_z1Jlyw', 'AIzaSyD_QitmGWO3QjifI52yB4FeJdkoPwHdsOQ',
                            'AIzaSyDDth5lclt7TnPuDoPHOfxAqHrL1F1M_M8', 'AIzaSyAhuMuunKMMJrzt0vvKo9cqo2niKPTID2w',
                            'AIzaSyDKyKzOI18D54F2GvfhgwvIDYwcecgyrHA', 'AIzaSyAqFDw3npWpahKGvkU0H74IgyuKG5Jdklk',
                            'AIzaSyBeg25ezuXLwArpfR9dqIJf3nx1FZSjSVI', 'AIzaSyANFPbjImRbyUhLVoVJVmJGlosly42wsko',
                            'AIzaSyA8glHavsT3PvhR0QXQ1sZo2oicY6inHNM', 'AIzaSyAPuIOAOsZGPZHTysk2IL9RFhuAcdTXQ2k',
                            'AIzaSyBadLMMMTNBvI4VcA90Yv8ohm_JXPDzBU0', 'AIzaSyBNqnLs8id1O_GzulhpjUtKRcV4-XzB6LQ',
                            'AIzaSyAmChcWJFtsIhHUQuMZxLFwedzSujIH_2k', 'AIzaSyADKp5fCp5N51BU2wx-C6ppGCbatcGc-Iw',
                            'AIzaSyD1l2t-CanZEjEfYCd5Htf29raweUvHhVI', 'AIzaSyDB2FurdBQ35RtOEGubgP9bQB8ghy-XSwA',
                            'AIzaSyB0a0utrKDGxITc0kHFaKbRnIMcew3T3L0', 'AIzaSyC3JtolzDfp0Q7sQMUeMF1qduPtRTZrNcQ',
                            'AIzaSyB2WiLNBo1BAdCky8_L7ZM4n1vPp_yMokA', 'AIzaSyCzWxro5gjIte5OlJmzEkVyud3SYWBJ--4',
                            'AIzaSyC2geXQREo9T8GAuFKz3rgH7Sp21GVQNC8', 'AIzaSyCE5psoO0tHcmf0NuXioPw5gH0DYBJrAP4',
                            'AIzaSyAiTft1FaQcaRcubYgf1ziLFcpfe8PEsxY', 'AIzaSyAlxtaQcs98eU_UK6RgTUVkEjOLJD8b0wg',
                            'AIzaSyCwJUzhqEVegMaSwcfjKE4Tn8A3c5AjUlg', 'AIzaSyCRCU2tBQ9Pc3qysRhArTzRSDivb53Hu6M',
                            'AIzaSyDxje9_6-tIiiqxUpaB-PvKFnVgY3TzQhU', 'AIzaSyBHdW2mTP3XPxXcpJUpz0xO5qs80MMsXl8',
                            'AIzaSyDWc4Q_buoEFL6fKtBRZCvwIDPHCbwH8zw', 'AIzaSyBu_7FriD3Eo8NTYiODAd-no6vvJy45qEA',
                            'AIzaSyBXtJcCFRWqSJzsBCtSB2IN1wF0nCIuG-s', 'AIzaSyATQ3HnF8VIAQwSWFXU0wcxN7ETEzmyDwc',
                            'AIzaSyDBKLkx9BqWd39MXv6uiVypnOQtnpykCuk', 'AIzaSyDorrNFXXjsYohpn4EpeJayiFbElT5sW-0',
                            'AIzaSyC2XFgOJHCs0oSjfMOr7m0ePXgKQpl_-rE', 'AIzaSyBYNWzOxWAwYhP4pzkUbqvH4UUnUnuzIs8',
                            'AIzaSyCPCEE6K-4lSghIz8Z_1PUwsbn_QDZOwX8', 'AIzaSyCulTqthgRhNSdD5a1817RMWti4onbwe4o',
                            'AIzaSyBMCKyFBoFtnFhnSDZr7JeFC72lM_qH5Gk', 'AIzaSyCMKYQED6VeHOhze4IJNUp6PHspWqomv6Q',
                            'AIzaSyCHEd8wVEShGJHcmobEtIrksS3I0lu1QUk', 'AIzaSyB6350MLugaHdEkpSixOTD8q8oA15gV8Jo']
        buildapis =    {'gkobu01-t': 'AIzaSyDDjj1kmr18XHDf2t_JdzbSMTSudkyUju4',
                        'gkobu02-t': 'AIzaSyAPwTTIHbotxSFnWUjOOVw5IP_zQXE7_rM',
                        'gkobu03-t': 'AIzaSyBA-ot8Qi-AWKYwXgfTg-GUvzXFQwvFLT0',
                        'gkobu04-t': 'AIzaSyDXiJ4FONjEOHDqteueUV9VzuAVg-LuYm0',
                        'gkobu05-t': 'AIzaSyCQpQOFzbSGptGU3k7oetM-kWtBqKDCPBA',
                        'gkobu06-t': 'AIzaSyCCGXA6cRu-ZEE7YZGxQjQWsVGZMiowRaI',
                        'gkobu07-t': 'AIzaSyDanqucjl3E9DadnX3rQYCcVeTN6aNIWJs',
                        'gkobu01-test': 'AIzaSyCaXmbENa07FejefmWxG5MAMrKydPce5Iw',
                        'gkobu02-test': 'AIzaSyCI7vUDxBWEBa2LqKH_Jtx4No6y14oCPWE',
                        'gkobu03-test': 'AIzaSyAR6c_wiDLNSQ6LmZqDOU1LMmL1OmglNAQ',
                        'gkobu04-test': 'AIzaSyAlTbHz1xU1AYwlnSJiBUVaMauQDKIfxmI',
                        'gkobu05-test': 'AIzaSyDY7PX7pUTcKzptvkly2SydDEY5JxrFxes',
                        'gkobu06-test': 'AIzaSyBU734k0gemq0Bquuk-eA53sGiYsLnFeJQ'}
        keyid = random.choice(list(buildapis))
        setaddon = xbmcaddon.Addon('plugin.video.youtube')
        logo = setaddon.getAddonInfo('icon')
        gkobuyoutubeprev = setaddon.getSetting('gkobusetyoutube')
        gkobuyoutubenew = '1.2'
        if gkobuyoutubeprev == '' or gkobuyoutubeprev is None:
            gkobuyoutubeprev = '0'
        if os.path.exists(os.path.join(addons_folder, 'plugin.video.youtube')) and str(gkobuyoutubenew) > str(gkobuyoutubeprev):
            if monitor.waitForAbort(0.5):
                sys.exit()
            notify.progress('Ξεκινάει η ρύθμιση του Youtube', t=1, image=logo)
            apikey = setaddon.getSetting('youtube.api.key')
            try:
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Εφαρμογή ρυθμίσεων Youtube...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                setaddon.setSetting('kodion.setup_wizard', 'false')
                setaddon.setSetting('kodion.setup_wizard.forced_runs', '2')
                setaddon.setSetting('kodion.video.quality.ask', 'true')
                setaddon.setSetting('kodion.video.quality', '4')
                if xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)'):
                    setaddon.setSetting('kodion.mpd.quality.selection', '4')
                setaddon.setSetting('youtube.language', 'el')
                setaddon.setSetting('youtube.region', 'GR')
                if apikey in badapis or apikey is None:
                    try:
                        xbmcvfs.delete(os.path.join(data_folder, 'plugin.video.youtube', 'api_keys.json'))
                    except: pass
                    setaddon.setSetting('youtube.api.key', buildapis[keyid])
                    setaddon.setSetting('youtube.api.id', keyid)
                    setaddon.setSetting('youtube.api.secret', 'None')
                setaddon.setSetting('gkobusetyoutube', gkobuyoutubenew)
                notify.progress('H ρύθμιση του Youtube ολοκληρώθηκε', t=1, image=logo)
            except BaseException:
                notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Youtube...', t=1, image=logo)
                # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Youtube...", xbmcgui.NOTIFICATION_INFO, 3000, False)
                return
        else:
            return
    except BaseException:
        # notify.progress('Αδυναμία εφαρμογής ρυθμίσεων Youtube...', t=1, image=logo)
        # xbmcgui.Dialog().notification("[B]GKoBu-Υπηρεσία Ενημέρωσης[/B]", "Αδυναμία εφαρμογής ρυθμίσεων Youtube...", xbmcgui.NOTIFICATION_INFO, 3000, False)
        return


if __name__ == '__main__':
    setYoutubeSettings()

