import os
import re
from urllib import parse

import xbmcvfs

from resources.lib.common import tools
from resources.lib.modules.globals import g

_INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*]')


def sanitize_path_component(name):
    if not name:
        return 'Unknown'
    name = str(name).strip().rstrip('.')
    name = _INVALID_PATH_CHARS_RE.sub('', name).strip()
    return name or 'Unknown'


def is_organize_enabled():
    return g.get_bool_setting('download.organize.enabled')


def _item_info(item_information):
    return (item_information or {}).get('info') or {}


def resolve_show_title(item_information):
    info = _item_info(item_information)
    title = info.get('tvshowtitle') or info.get('title') or 'Unknown'
    return sanitize_path_component(title)


def resolve_movie_title(item_information):
    info = _item_info(item_information)
    title = info.get('title') or 'Unknown'
    return sanitize_path_component(title)


def resolve_library_root(item_information):
    if not g.get_bool_setting('download.organize.splitLibrary'):
        return ''
    mediatype = _item_info(item_information).get('mediatype')
    is_anime = tools.is_anime_by_genre(item_information)
    if mediatype == g.MEDIA_EPISODE:
        return 'Anime' if is_anime else 'TV Shows'
    if mediatype == g.MEDIA_MOVIE:
        return 'Anime' if is_anime else 'Movies'
    return ''


def resolve_season_folder(item_information):
    if not g.get_bool_setting('download.organize.tvSeasonFolders'):
        return ''
    try:
        season = int(_item_info(item_information).get('season'))
    except (TypeError, ValueError):
        return ''
    return f'Season {season:02d}'


def build_download_subdir(item_information):
    if not is_organize_enabled() or not item_information:
        return ''
    info = _item_info(item_information)
    mediatype = info.get('mediatype')
    parts = []

    library_root = resolve_library_root(item_information)
    if library_root:
        parts.append(library_root)

    if mediatype == g.MEDIA_EPISODE:
        parts.append(resolve_show_title(item_information))
        season_folder = resolve_season_folder(item_information)
        if season_folder:
            parts.append(season_folder)
    elif mediatype == g.MEDIA_MOVIE:
        title = resolve_movie_title(item_information)
        if g.get_bool_setting('download.organize.movieYear'):
            year = info.get('year')
            if year:
                title = f'{title} ({year})'
        parts.append(title)
    else:
        return ''

    return os.path.join(*parts) if parts else ''


def ensure_directory(path):
    if path and not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(tools.validate_path(path))


def join_download_path(storage_root, subdir, filename):
    storage_root = tools.validate_path((storage_root or '').rstrip('/\\'))
    filename = os.path.basename(parse.unquote(filename or ''))
    if subdir:
        dest_dir = os.path.join(storage_root, subdir.replace('/', os.sep))
        ensure_directory(dest_dir)
        return tools.validate_path(os.path.join(dest_dir, filename))
    ensure_directory(storage_root)
    return tools.validate_path(os.path.join(storage_root, filename))


def _normalize_path(path):
    return os.path.normpath(tools.validate_path(path))


def _move_file(source, dest):
    if xbmcvfs.rename(source, dest):
        return True
    if xbmcvfs.copy(source, dest):
        if not xbmcvfs.delete(source):
            g.log(f"Moved to local library but failed to delete source: {source}", "warning")
        return True
    return False


def move_to_local_library(completed_file_path):
    """No-op passthrough unless download.automoveToLocal is enabled and both
    local.location/download.location are configured - safe to call unconditionally."""
    if not g.get_bool_setting('download.automoveToLocal'):
        return completed_file_path

    local_root = (g.get_setting('local.location') or '').strip()
    download_root = (g.get_setting('download.location') or '').strip()
    if not local_root or not download_root:
        return completed_file_path

    if not xbmcvfs.exists(completed_file_path):
        g.log(f"Auto-move: source file does not exist: {completed_file_path}", "warning")
        return completed_file_path

    source_path = _normalize_path(completed_file_path)
    download_root = _normalize_path(download_root)
    local_root = _normalize_path(local_root)

    relative = os.path.relpath(source_path, download_root)
    if relative.startswith('..'):
        g.log(f"Auto-move: {source_path} is not under download.location, skipping", "warning")
        return completed_file_path

    dest = os.path.join(local_root, relative)
    if xbmcvfs.exists(dest):
        g.log(f"Auto-move: destination already exists, skipping: {dest}", "warning")
        return completed_file_path

    ensure_directory(os.path.dirname(dest))
    if not _move_file(source_path, dest):
        g.log(f"Auto-move: failed to move {source_path} to {dest}", "error")
        return completed_file_path

    g.log(f"Auto-move: moved {source_path} to {dest}")
    _cleanup_empty_dirs(os.path.dirname(source_path), download_root)
    return dest


def _cleanup_empty_dirs(start_dir, stop_at):
    current = _normalize_path(start_dir)
    stop_at = _normalize_path(stop_at.rstrip('/\\'))
    while current and current.lower() != stop_at.lower():
        try:
            dirs, files = xbmcvfs.listdir(current)
            if dirs or files:
                break
            if not xbmcvfs.rmdir(current):
                break
        except (OSError, ValueError):
            break
        current = os.path.dirname(current)
