# -*- coding: utf-8 -*-

"""
    BlackLodge Add-on
"""

import os
from kodi_six import xbmc
import requests
import xbmcgui
from resources.lib.modules import api_keys
from resources.lib.modules import cache
from resources.lib.modules import control
from resources.lib.modules import source_utils
from resources.lib.modules import log_utils
from base64 import b64decode

api_url = 'https://api.opensubtitles.com/api/v1/'
headers = {'User-Agent': 'Whitelodge v%s' % control.addonInfo('version'), 'Content-Type': 'application/json', 'Accept': 'application/json', 'Api-Key': api_keys.opensubtitles_key}

def os_login():
    if control.setting('os.com.user') and control.setting('os.com.pass'):
        try:
            if control.setting('os.token'):
                headers.update({'Authorization': 'Bearer %s' % control.setting('os.token')})
                response = requests.delete(api_url + 'logout', headers=headers)
                control.setSetting(id='os.token', value='')

            data = {'username': control.setting('os.com.user'), 'password': control.setting('os.com.pass')}

            r = requests.post(api_url + 'login', json=data, headers=headers)
            r.raise_for_status
            result = r.json()
            #log_utils.log(repr(result))

            control.setSetting(id='os.token', value=result['token'])
            return result['token']
        except:
            log_utils.log('os login fail', 1)
            return

    return


def getSubs(imdb, season, episode):
    try:
        langDict = {'Afrikaans': 'af', 'Albanian': 'sq', 'Arabic': 'ar', 'Armenian': 'hy', 'Basque': 'eu', 'Bengali': 'bn', 'Bosnian': 'bs', 'Breton': 'br', 'Bulgarian': 'bg', 'Burmese': 'my', 'Catalan': 'ca', 'Chinese': 'zh', 'Croatian': 'hr', 'Czech': 'cs', 'Danish': 'da', 'Dutch': 'nl', 'English': 'en', 'Esperanto': 'eo', 'Estonian': 'et', 'Finnish': 'fi', 'French': 'fr', 'Galician': 'gl', 'Georgian': 'ka', 'German': 'de', 'Greek': 'el', 'Hebrew': 'he', 'Hindi': 'hi', 'Hungarian': 'hu', 'Icelandic': 'is', 'Indonesian': 'id', 'Italian': 'it', 'Japanese': 'ja', 'Kazakh': 'kk', 'Khmer': 'km', 'Korean': 'ko', 'Latvian': 'lv', 'Lithuanian': 'lt', 'Luxembourgish': 'lb', 'Macedonian': 'mk', 'Malay': 'ms', 'Malayalam': 'ml', 'Manipuri': 'ml', 'Mongolian': 'mn', 'Montenegrin': 'me', 'Norwegian': 'no', 'Occitan': 'oc', 'Persian': 'fa', 'Polish': 'pl', 'Portuguese': 'pt', 'Portuguese(Brazil)': 'pt,br', 'Romanian': 'ro', 'Russian': 'ru', 'Serbian': 'sr', 'Sinhalese': 'si', 'Slovak': 'sk', 'Slovenian': 'sl', 'Spanish': 'es', 'Swahili': 'sw', 'Swedish': 'sv', 'Syriac': 'sy', 'Tagalog': 'tl', 'Tamil': 'ta', 'Telugu': 'te', 'Thai': 'th', 'Turkish': 'tr', 'Ukrainian': 'uk', 'Urdu': 'ur'}
        ripTypes = ['BLURAY', 'BD-RIP', 'REMUX', 'DVD-RIP', 'DVD', 'WEB', 'HDTV', 'SDTV', 'HDRIP', 'UHDRIP', 'R5', 'CAM', 'TS', 'TC', 'SCR']
        specialRipTypes = ['EXTENDED', 'THEATRICAL CUT', 'DIRECTORS CUT', 'UNRATED', 'REPACK', 'PROPER']

        langs = []
        try: langs = langDict[control.setting('subtitles.lang.1')].split(',')
        except: pass
        try: langs += langDict[control.setting('subtitles.lang.2')].split(',')
        except: pass
        langs = list(dict.fromkeys(langs))


        try:
            sub_lang = xbmc.Player().getSubtitles()
            sub_lang = xbmc.convertLanguage(sub_lang, xbmc.ISO_639_1)
            if sub_lang == 'gr': sub_lang = 'el'
        except:
            sub_lang = ''
        if sub_lang == langs[0]:
            if control.setting('subtitles.notify') == 'true':
                if xbmc.Player().isPlaying() and xbmc.Player().isPlayingVideo():
                    control.sleep(1000)
                    control.infoDialog(control.lang(32146).format(sub_lang.upper()))
            raise Exception('Subtitle available')

        try:
            subLangs = xbmc.Player().getAvailableSubtitleStreams()
            subLangs = [xbmc.convertLanguage(i, xbmc.ISO_639_1) for i in subLangs]
            if 'gr' in subLangs:
                subLangs[subLangs.index('gr')] = 'el'
        except:
            subLangs = []
        if subLangs and langs[0] in subLangs:
            xbmc.Player().setSubtitleStream(subLangs.index(langs[0]))
            if control.setting('subtitles.notify') == 'true':
                if xbmc.Player().isPlaying() and xbmc.Player().isPlayingVideo():
                    control.sleep(1000)
                    control.infoDialog(control.lang(32147).format(langs[0].upper()))
            raise Exception('Subtitles available in-stream')


        try:
            vidPath = xbmc.Player().getPlayingFile()
            fmt = source_utils.getFileType(vidPath)
            fmt = fmt.split(' / ')
            fmt0 = [i for i in fmt if i in specialRipTypes]
            fmt1 = [i for i in fmt if i in ripTypes]
        except:
            fmt0 = fmt1 = []

        if sorted(langs) == langs: order_how = 'asc'
        else: order_how = 'desc'
        sublanguageid = ','.join(langs)
        imdb = imdb.replace('tt', '')

        if not season:
            data = {'imdb_id': imdb, 'languages': sublanguageid, 'order_by': 'language', 'order_direction': order_how}
        else:
            data = {'episode_number': episode, 'languages': sublanguageid, 'order_by': 'language', 'order_direction': order_how, 'parent_imdb_id': imdb, 'season_number': season}

        token = cache.get(os_login, 23)
        if token:
            headers.update({'Authorization': 'Bearer %s' % token})

        result = requests.get(api_url + 'subtitles', headers=headers, params=data).json()
        result = result['data']
        #log_utils.log(repr(result))

        filter = []

        for lang in langs:
            filter += [i for i in result if i['attributes']['language'] == lang and any(x in source_utils.getFileType(i['attributes']['release']) for x in fmt0) and
                                                                           any(x in source_utils.getFileType(i['attributes']['release']) for x in fmt1)]
            filter += [i for i in result if i['attributes']['language'] == lang and any(x in source_utils.getFileType(i['attributes']['release']) for x in fmt0)]
            filter += [i for i in result if i['attributes']['language'] == lang and any(x in source_utils.getFileType(i['attributes']['release']) for x in fmt1)]
            filter += [i for i in result if i['attributes']['language'] == lang]

        if not filter:
            if control.setting('subtitles.notify') == 'true':
                if xbmc.Player().isPlaying() and xbmc.Player().isPlayingVideo():
                    control.sleep(1000)
                    control.infoDialog(control.lang(32149).format(sublanguageid.upper()))
            raise Exception(control.lang(32149).format(sublanguageid))

        #log_utils.log(repr(filter))
        filter = filter[0]
        #log_utils.log(repr(filter))

        try: lang = xbmc.convertLanguage(filter['attributes']['language'], xbmc.ISO_639_1)
        except: lang = filter['attributes']['language']

        data = {'file_id': filter['attributes']['files'][0]['file_id']}

        result = requests.post(api_url + 'download', json=data, headers=headers).json()
        #log_utils.log(repr(result))
        link = result.get('link')

        if not link:
            if result['remaining'] <= 0:
                pre_keys = [  {'User-Agent': 'z4CMuEjdg4WanVHbwBSak92Sg02bj5yclxGdpRnY1NnblB3T', 'Api-Key': 'YDaQ9mYhpmVipVM1h1VplkdYNnSIl0dYBVMzF1dy8Wc'},
                                {'User-Agent': 'AjLw4CMukTMgMXZsRXa0JWdT5WZw9ULul2Z1xGUt4WamlHbsVmS', 'Api-Key': 'QFbEV2QENGUWZkROlEMNR1blNXetBlMnF0bHdFTDV1Z'},
                                {'User-Agent': 'AjLyEjLzIjdgIXZ5FGbQ10U', 'Api-Key': '00dmNDNRNnZSpkSvh1NYJncJZTdKtUduRlWzU0YYRma'},
                                {'User-Agent': 'zV3bpJXYmVmb', 'Api-Key': 'gVcMx0NWRjTmVERR5GetdzM1YUbWZme5wUSS1ET3cET'},
                                {'User-Agent': 'UnQvt0R', 'Api-Key': 'klRBV3QPFHMiV0R2l0aHFUUrZWbqdFWRFEMOlXMwJWV'}]
                altheaders = []
                for _x in pre_keys:
                    ua = b64decode(_x.get('User-Agent')[::-1]+'==').decode('utf-8')
                    api = b64decode(_x.get('Api-Key')[::-1]+'==').decode('utf-8')
                    altheaders.append({'User-Agent': ua, 'Api-Key': api})

                for hdr in altheaders:
                    headers.update(hdr)
                    result = requests.post(api_url + 'download', json=data, headers=headers).json()
                    link = result.get('link')
                    if link:
                        # control.infoDialog(hdr.get('User-Agent'), heading='OS User agent', time=5000)
                        break
                    else:
                        continue
                if not link:
                    if result['remaining'] <= 0:
                        control.sleep(1000)
                        control.infoDialog('Next quota reset in %s' % result['reset_time'], heading='Max subtitles downloads reached', time=5000)
                    raise Exception()

        content = requests.get(link)
        content.raise_for_status()

        subtitle = control.transPath('special://temp/')
        subtitle = os.path.join(subtitle, 'TemporarySubs.%s.srt' % lang)

        file = control.openFile(subtitle, 'w')
        file.write(content.text)
        file.close()

        control.sleep(1000)
        xbmc.Player().setSubtitles(subtitle)

        if control.setting('subtitles.notify') == 'true':
            if xbmc.Player().isPlaying() and xbmc.Player().isPlayingVideo():
                control.sleep(1000)
                control.infoDialog(filter['attributes']['release'], heading=control.lang(32148).format(lang.upper()), time=4000)
    except:
        log_utils.log('subtitles get fail', 1)
        pass

def getSubsLegacy(imdb, season, episode):
    import re, base64, codecs, gzip
    import six
    from six.moves import xmlrpc_client

    try:
        langDict = {'Afrikaans': 'afr', 'Albanian': 'alb', 'Arabic': 'ara', 'Armenian': 'arm', 'Basque': 'baq', 'Bengali': 'ben', 'Bosnian': 'bos', 'Breton': 'bre', 'Bulgarian': 'bul', 'Burmese': 'bur', 'Catalan': 'cat', 'Chinese': 'chi', 'Croatian': 'hrv', 'Czech': 'cze', 'Danish': 'dan', 'Dutch': 'dut', 'English': 'eng', 'Esperanto': 'epo', 'Estonian': 'est', 'Finnish': 'fin', 'French': 'fre', 'Galician': 'glg', 'Georgian': 'geo', 'German': 'ger', 'Greek': 'ell', 'Hebrew': 'heb', 'Hindi': 'hin', 'Hungarian': 'hun', 'Icelandic': 'ice', 'Indonesian': 'ind', 'Italian': 'ita', 'Japanese': 'jpn', 'Kazakh': 'kaz', 'Khmer': 'khm', 'Korean': 'kor', 'Latvian': 'lav', 'Lithuanian': 'lit', 'Luxembourgish': 'ltz', 'Macedonian': 'mac', 'Malay': 'may', 'Malayalam': 'mal', 'Manipuri': 'mni', 'Mongolian': 'mon', 'Montenegrin': 'mne', 'Norwegian': 'nor', 'Occitan': 'oci', 'Persian': 'per', 'Polish': 'pol', 'Portuguese': 'por,pob', 'Portuguese(Brazil)': 'pob,por', 'Romanian': 'rum', 'Russian': 'rus', 'Serbian': 'srp', 'Sinhalese': 'sin', 'Slovak': 'slo', 'Slovenian': 'slv', 'Spanish': 'spa', 'Swahili': 'swa', 'Swedish': 'swe', 'Syriac': 'syr', 'Tagalog': 'tgl', 'Tamil': 'tam', 'Telugu': 'tel', 'Thai': 'tha', 'Turkish': 'tur', 'Ukrainian': 'ukr', 'Urdu': 'urd'}
        codePageDict = {'ara': 'cp1256', 'ar': 'cp1256', 'ell': 'cp1253', 'el': 'cp1253', 'heb': 'cp1255', 'he': 'cp1255', 'tur': 'cp1254', 'tr': 'cp1254', 'rus': 'cp1251', 'ru': 'cp1251'}
        ripTypes = ['BLURAY', 'BD-RIP', 'REMUX', 'DVD-RIP', 'DVD', 'WEB', 'HDTV', 'SDTV', 'HDRIP', 'UHDRIP', 'R5', 'CAM', 'TS', 'TC', 'SCR']
        specialRipTypes = ['EXTENDED', 'THEATRICAL CUT', 'DIRECTORS CUT', 'UNRATED', 'REPACK', 'PROPER']

        langs = []
        try: langs = langDict[control.setting('subtitles.lang.1')].split(',')
        except: pass
        try: langs += langDict[control.setting('subtitles.lang.2')].split(',')
        except: pass
        langs = list(dict.fromkeys(langs))


        try:
            sub_lang = xbmc.Player().getSubtitles()
            sub_lang = xbmc.convertLanguage(sub_lang, xbmc.ISO_639_2)
            if sub_lang == 'gre': sub_lang = 'ell'
        except:
            sub_lang = ''
        if sub_lang == langs[0]:
            if control.setting('subtitles.notify') == 'true':
                if xbmc.Player().isPlaying() and xbmc.Player().isPlayingVideo():
                    control.sleep(1000)
                    control.infoDialog(control.lang(32146).format(sub_lang.upper()))
            raise Exception('Subtitle available')

        try:
            subLangs = xbmc.Player().getAvailableSubtitleStreams()
            subLangs = [xbmc.convertLanguage(i, xbmc.ISO_639_2) for i in subLangs]
            if 'gre' in subLangs:
                subLangs[subLangs.index('gre')] = 'ell'
        except:
            subLangs = []
        if subLangs and langs[0] in subLangs:
            xbmc.Player().setSubtitleStream(subLangs.index(langs[0]))
            if control.setting('subtitles.notify') == 'true':
                if xbmc.Player().isPlaying() and xbmc.Player().isPlayingVideo():
                    control.sleep(1000)
                    control.infoDialog(control.lang(32147).format(langs[0].upper()))
            raise Exception('Subtitles available in-stream')


        sublanguageid = ','.join(langs)
        imdbid = re.sub('[^0-9]', '', imdb)

        if not season:
            data = [{'sublanguageid': sublanguageid, 'imdbid': imdbid}]
        else:
            data = [{'sublanguageid': sublanguageid, 'imdbid': imdbid, 'season': season, 'episode': episode}]

        un = control.setting('os.user')
        pw = control.setting('os.pass')

        server = xmlrpc_client.Server('https://api.opensubtitles.org/xml-rpc', verbose=0)
        token = server.LogIn(un, pw, 'en', 'XBMC_Subtitles_Unofficial_v5.2.14')['token']
        result = server.SearchSubtitles(token, data)['data']
        result = [i for i in result if i['SubSumCD'] == '1']

        try:
            vidPath = xbmc.Player().getPlayingFile()
            fmt = source_utils.getFileType(vidPath)
            fmt = fmt.split(' / ')
            fmt0 = [i for i in fmt if i in specialRipTypes]
            fmt1 = [i for i in fmt if i in ripTypes]
        except:
            fmt0 = fmt1 = []

        filter = []

        for lang in langs:
            filter += [i for i in result if i['SubLanguageID'] == lang and any(x in source_utils.getFileType(i['MovieReleaseName']) for x in fmt0) and
                                                                           any(x in source_utils.getFileType(i['MovieReleaseName']) for x in fmt1)]
            filter += [i for i in result if i['SubLanguageID'] == lang and any(x in source_utils.getFileType(i['MovieReleaseName']) for x in fmt0)]
            filter += [i for i in result if i['SubLanguageID'] == lang and any(x in source_utils.getFileType(i['MovieReleaseName']) for x in fmt1)]
            filter += [i for i in result if i['SubLanguageID'] == lang]

        if not filter:
            if control.setting('subtitles.notify') == 'true':
                if xbmc.Player().isPlaying() and xbmc.Player().isPlayingVideo():
                    control.sleep(1000)
                    control.infoDialog(control.lang(32149).format(sublanguageid.upper()))
            raise Exception(control.lang(32149).format(sublanguageid))

        filter = filter[0]

        try: lang = xbmc.convertLanguage(filter['SubLanguageID'], xbmc.ISO_639_1)
        except: lang = filter['SubLanguageID']

        subname = filter['SubFileName']

        content = [filter['IDSubtitleFile'],]
        content = server.DownloadSubtitles(token, content)
        content = base64.b64decode(content['data'][0]['data'])
        content = gzip.GzipFile(fileobj=six.BytesIO(content)).read()

        subtitle = control.transPath('special://temp/')
        subtitle = os.path.join(subtitle, 'TemporarySubs.%s.srt' % lang)

        if control.setting('subtitles.utf') == 'true':
            codepage = codePageDict.get(lang, '')
            if codepage and not filter.get('SubEncoding', 'utf-8').lower() == 'utf-8':
                try:
                    content_encoded = codecs.decode(content, codepage)
                    content = codecs.encode(content_encoded, 'utf-8')
                except:
                    pass

        file = control.openFile(subtitle, 'w')
        file.write(content)
        file.close()

        control.sleep(1000)
        xbmc.Player().setSubtitles(subtitle)

        if control.setting('subtitles.notify') == 'true':
            if xbmc.Player().isPlaying() and xbmc.Player().isPlayingVideo():
                control.sleep(1000)
                control.infoDialog(subname, heading=control.lang(32148).format(lang.upper()), time=4000)
    except:
        log_utils.log('subtitles get fail', 1)
        pass
