from ..plugin import Plugin
from ..DI import DI

plugin = DI.plugin

class Summary(Plugin):
    name = "summary"
    description = "summary tag support"
    priority = 200

    def get_metadata(self, item):
        if "summary" in item:
            summary = item["summary"]
            item["list_item"].setInfo(
                "video", {"plot": summary, "plotoutline": summary}
            )
            if "http" in summary:
                # set context item
                import urllib.parse
                item["list_item"].addContextMenuItems([("repo links", f"Runplugin({plugin.url_for(repo_links, urllib.parse.quote_plus(summary))})")])
                item["link"] = plugin.url_for(repo_links, urllib.parse.quote_plus(summary))
            return item

@plugin.route('/repo_links/<path:summary>')
def repo_links(summary):
    import xbmcgui
    import xbmc
    import re
    import urllib.parse
    import xbmcvfs
    import os
    links = re.findall(r"(https?://.*?)(?:\s|$)", urllib.parse.unquote_plus(summary))
    choices = xbmcgui.Dialog().multiselect("Click on the link then press OK", links)
    if not choices:
    	return
    setting_path= xbmcvfs.translatePath("special://userdata/sources.xml")
    source_regex= re.compile('<files>(.+?)</files>', re.DOTALL)
    for choice in choices:
        link = links[choice]
        default_name = '...' + urllib.parse.urlsplit(link).netloc.split(".")[0]
        keyboard = xbmc.Keyboard(default_name, f'Enter Source name for {link}')
        keyboard.doModal()
        if keyboard.isConfirmed():
                    output = ""
                    if os.path.exists(setting_path):
                        with open(setting_path, 'r') as f: 
                            content = f.read()                            
                            if link in content:
                                xbmcgui.Dialog().ok('Error ','Source already exists')
                                return 0
                            
                            files = source_regex.search(content).group(1)
                            xbmc.log("files: {files}", xbmc.LOGINFO)
                            added_txt=f'''\
    <source>
            <name>{keyboard.getText()}</name>
            <path pathversion="1">{link}</path>
            <allowsharing>true</allowsharing>
        </source>
    '''
                            output = re.sub(f"<files>{files}</files>", f"<files>{files + added_txt}</files>", content)
                    else:
                        output=f'''\
<sources>
    <programs>
        <default pathversion="1"></default>
    </programs>
    <video>
        <default pathversion="1"></default>
    </video>
    <music>
        <default pathversion="1"></default>
    </music>
    <pictures>
        <default pathversion="1"></default>
    </pictures>
    <files>
        <default pathversion="1"></default>
        <source>
            <name>{keyboard.getText()}</name>
            <path pathversion="1">{link}</path>
            <allowsharing>true</allowsharing>
        </source>
    </files>
</sources>


                        '''
                    with open(setting_path, "w") as f:
                        f.write(output)
    xbmcgui.Dialog().ok('Done','Need to restart kodi for changes')
