import sys
import xbmc, xbmcgui
# Py3
try:
    from urllib.parse import quote

# Py2:
except ImportError:
    from urllib import quote

if __name__ == '__main__':
    # Extract the info we'll send over to Skin Shortcuts
    filename = sys.listitem.getPath()
    label = sys.listitem.getLabel()
    icon = xbmc.getInfoLabel( "ListItem.Icon" )
    content = xbmc.getInfoLabel( "Container.Content" )
    window = xbmcgui.getCurrentWindowId()

    # Call Skin Shortcuts
    runScript = "RunScript(script.skinshortcuts,type=context&filename=%s&label=%s&icon=%s&content=%s&window=%s)" %( quote( filename ), label, icon, content, window )
    xbmc.executebuiltin( "%s" %( runScript ) )
