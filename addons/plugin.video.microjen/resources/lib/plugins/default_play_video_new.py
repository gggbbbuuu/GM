from ..plugin import Plugin
import xbmc, xbmcgui, xbmcaddon, xbmcplugin
import json, sys
import resolveurl

addon_id = xbmcaddon.Addon().getAddonInfo('id')
default_icon = xbmcaddon.Addon(addon_id).getAddonInfo('icon')
default_fanart = xbmcaddon.Addon(addon_id).getAddonInfo('fanart')

def isList(item):
	if isinstance(item,list):
		return True
	else:
		return False

class default_play_video(Plugin):
    name = "default video playback"
    priority = 0

    def play_video(self, item):
        item = json.loads(item)
        link = item["link"]
        play_link= '' 
        if isList(link):
        	if len(link) > 1:
        		labels = []
        		counter = 1
        		for x in link:
        			if x.strip().endswith(')'):
        				label = x.split('(')[-1].replace(')', '')
        			else:
        				label = 'Link ' + str(counter)
        			labels.append(label)
        			counter += 1		
       			dialog = xbmcgui.Dialog()
       			ret = dialog.select('Choose a Link', labels)
       			if ret == -1:
       				return
       			else:
       				if link[ret].strip().endswith(')'):
       					link = link[ret].rsplit('(')[0].strip()     
       					play_link= link                           
       				else:
       					link = link[ret]
       					play_link= link
        	else:
        		if link[0].strip().endswith(')'):
        			link = link[0].rsplit('(')[0].strip()  
        			play_link= link
        		else:
        			link = link[0]
        			play_link= link
        else:
        	link = item["link"]
        	play_link= link
        
        title = item["title"]
        thumbnail = item.get("thumbnail", default_icon)
        liz = xbmcgui.ListItem(title)
        liz.setInfo('video', {'Title': title})
        liz.setArt({'thumb': thumbnail, 'icon': thumbnail})
        
        
        if play_link :
            if resolveurl.HostedMediaFile(link).valid_url():
        	    url = resolveurl.HostedMediaFile(link).resolve()
        	    return xbmc.Player().play(url,liz)
        
            elif 'dailymotion' in link.lower():
                try : 
                    # u = 'plugin.video.dailymotion_com' + ',' + link.split('?')[-1]
                    z = 'plugin://plugin.video.dailymotion_com/?'+ link.split('?')[-1]
                    xbmc.executebuiltin('PlayMedia({})'.format(z))
                    return True  
                except Exception as e:         
                    pass
                try :                 
                    r = re.findall(r"dailymotion\.com\/video\/(\S+)", link)
                    if len(r) > 0:
                        xbmc.executebuiltin('RunPlugin(plugin://plugin.video.dailymotion_com/?mode=playVideo&url=%s)' % r[0])
                        return True     
                except Exception as e:
                    pass
        
            elif 'youtube' in link.lower():
                try : 
                    r = re.findall(r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})", link)
                    if len(r) > 0:
                        xbmc.executebuiltin(f"RunPlugin(plugin://plugin.video.youtube/play/?video_id={r[0]})")
                        return True
                except Exception as e:
                    pass
    
            elif link.startswith("is_mpd://"):
                title = item.get("title")
                thumbnail = item.get("thumbnail", "")
                mpd_split = link.split("===")
                mpd_url = mpd_split[0].replace("is_mpd://", "")
                license_key = mpd_split[1]
                is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
                if not is_helper.check_inputstream():
                    sys.exit()
                liz = xbmcgui.ListItem(item.get("title", mpd_url), path=mpd_url)
                if int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0]) >= 19: liz.setProperty('inputstream', 'inputstream.adaptive')
                else: liz.setProperty('inputstreamaddon', 'inputstream.adaptive')
                liz.setProperty('inputstream.adaptive.manifest_type', 'mpd')

                if license_key != '':
                    liz.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
                    liz.setProperty('inputstream.adaptive.license_key', license_key)
                liz.setMimeType('application/dash+xml')
                liz.setContentLookup(False)
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
                xbmc.Player().play(mpd_url, listitem=liz)      
                return True      
            
            elif link.startswith("is_ffmpeg://"):
                title = item.get("title")
                thumbnail = item.get("thumbnail", "")
                m3u8_url = link.replace("is_ffmpeg://", "")
                liz = xbmcgui.ListItem(item.get("title", m3u8_url), path=m3u8_url)
                
                liz.setInfo('video', {'Title': title})
                liz.setArt({'thumb': thumbnail, 'icon': thumbnail})
                
                if int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0]) >= 19: liz.setProperty('inputstream', 'inputstream.ffmpegdirect')
                else: liz.setProperty('inputstreamaddon', 'inputstream.ffmpegdirect')
                liz.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
                liz.setProperty('inputstream.ffmpegdirect.stream_mode', 'timeshift')
                liz.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')
                liz.setMimeType('application/x-mpegURL')
                xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
                xbmc.Player().play(m3u8_url, listitem=liz)            
                return True
    
            else:
        	    return xbmc.Player().play(link,liz)
       
       