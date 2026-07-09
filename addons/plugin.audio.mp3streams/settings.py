import xbmcvfs
import xbmcaddon
import os
import html

ADDON = xbmcaddon.Addon(id='plugin.audio.mp3streams')
DATA_PATH = os.path.join(xbmcvfs.translatePath('special://profile/addon_data/plugin.audio.mp3streams'), '')

def cookie_jar():
    return create_file(DATA_PATH, "cookiejar.lwp")
	
def addon():
    return ADDON
		
def artist_icons():
    return create_directory(DATA_PATH, "artist_icons")
	
def folder_structure():
    return ADDON.getSetting('folder_structure')
	
def favourites_file_artist():
    return create_file(DATA_PATH, "favourites_artist.list")
	
def favourites_file_album():
    return create_file(DATA_PATH, "favourites_album.list")
	
def download_list():
    return create_file(DATA_PATH, "downloads.list")
	
def favourites_file_songs():
    return create_file(DATA_PATH, "favourites_songs.list")
	
def playlist_file():
    return create_file(DATA_PATH, "playlist_file.list")
	
def uses_custom_music_dir():
    mode = ADDON.getSetting('music_dir_mode')
    if mode in ('1', 'Custom folder'):
        return True
    if mode in ('0', 'Default folder'):
        return False
    return ADDON.getSetting('custom_directory') == 'true'

def custom_directory():
    return uses_custom_music_dir()
		
def keep_downloads():
    if ADDON.getSetting('keep_downloads') == "true":
        return True
    else:
        return False
		
def gotham_fix():
    if ADDON.getSetting('gotham_fix') == "true":
        return True
    else:
        return False
		
def golden_path():
    if ADDON.getSetting('golden_path') == "true":
        return True
    else:
        return False
		
def default_queue():
    if ADDON.getSetting('default_queue') == "true":
        return True
    else:
        return False
		
def hide_fanart():
    if ADDON.getSetting('hide_fanart') == "true":
        return True
    else:
        return False
		
def default_queue_album():
    if ADDON.getSetting('default_queue_album') == "true":
        return True
    else:
        return False
		
def default_music_dir():
    return create_directory(DATA_PATH, "music")

def music_dir():
    if not uses_custom_music_dir():
        return default_music_dir()
    folder = ADDON.getSetting('music_dir')
    if not folder or folder == 'set':
        return default_music_dir()
    folder = xbmcvfs.translatePath(folder)
    return create_directory(folder, "")
	
def decode_text(text):
    if not text:
        return text
    return html.unescape(text)

def sanitize_filename(text):
    if not text:
        return text
    text = decode_text(text)
    for char, replacement in (
        ('/', ' - '),
        ('\\', ' - '),
        (':', ' -'),
        ('*', ''),
        ('?', ''),
        ('"', ''),
        ('<', ''),
        ('>', ''),
        ('|', ''),
    ):
        text = text.replace(char, replacement)
    return text.strip()

def create_directory(dir_path, dir_name=None):
    if dir_name:
        dir_path = os.path.join(dir_path, sanitize_filename(dir_name))
    dir_path = dir_path.strip()
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path

def create_file(dir_path, file_name=None):
    if file_name:
        file_path = os.path.join(dir_path, sanitize_filename(file_name))
    file_path = file_path.strip()
    if not os.path.exists(file_path):
        f = open(file_path, 'w')
        f.write('')
        f.close()
    return file_path
	
create_directory(DATA_PATH, "")
   
