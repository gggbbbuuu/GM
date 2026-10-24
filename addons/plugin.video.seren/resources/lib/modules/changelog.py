import xbmcgui

from resources.lib.modules.globals import g


def show_changelog():
    text = g.ADDON.getAddonInfo("changelog")
    text = "\n".join(line.strip() for line in text.splitlines()).strip()
    heading = f"{g.ADDON_NAME} v{g.VERSION} - {g.get_language_string(31165)}"
    xbmcgui.Dialog().textviewer(heading, text)
