# -*- coding: utf-8 -*-
"""
Dynamic scraper addon detection and management
Supports multiple forks of cocoscrapers and similar scraper packages
"""

import os
import sys
import xbmcaddon
import xbmc
import xbmcvfs
import json

from resources.modules import log

Addon = xbmcaddon.Addon('plugin.video.shadow')


def get_scraper_abbreviation(addon_id):
    """
    Generate a 3-letter abbreviation for a scraper addon
    
    Args:
        addon_id (str): The addon ID
    
    Returns:
        str: 3-letter abbreviation (lowercase)
    """
    # Manual mappings for common scrapers
    mappings = {
        'script.module.cocoscrapers': 'coc',
        'plugin.program.taz19scrapers': 'taz',
    }
    
    if addon_id in mappings:
        return mappings[addon_id]
    
    # Generate from addon name if not in mappings
    # Remove common prefixes
    name = addon_id.replace('script.module.', '').replace('plugin.program.', '')
    
    # Take first 3 letters, make lowercase
    abbr = name[:3].lower()
    return abbr if len(abbr) == 3 else (abbr + 'x' * (3 - len(abbr)))


def xbmc_tranlate_path(path):
    """Translate special:// paths to actual filesystem paths"""
    return xbmcvfs.translatePath(path)


def detect_scraper_addons():
    """
    Dynamically detect all available scraper addons
    Looks for addons with xbmc.python.module that contain sources_* directories
    
    Returns:
        list: List of dicts with addon info: 
        {
            'id': 'addon.id',
            'name': 'Addon Name',
            'path': '/full/path/to/addon',
            'lib_path': '/full/path/to/lib',
            'sources_info': {'directory': 'sources_modulename', 'location': 'lib' or 'lib/module'}
        }
    """
    addons_path = xbmc_tranlate_path('special://home/addons')
    detected_scrapers = []
    
    if not os.path.exists(addons_path):
        log.warning('Addons path not found: %s' % addons_path)
        return detected_scrapers
    
    try:
        addon_dirs = os.listdir(addons_path)
    except Exception as e:
        log.warning('Error reading addons directory: %s' % str(e))
        return detected_scrapers
    
    for addon_dir in addon_dirs:
        addon_path = os.path.join(addons_path, addon_dir)
        
        # Skip if not a directory
        if not os.path.isdir(addon_path):
            continue
        
        # Look for addon.xml
        addon_xml = os.path.join(addon_path, 'addon.xml')
        if not os.path.exists(addon_xml):
            continue
        
        # Check if it's a module addon (xbmc.python.module)
        try:
            with open(addon_xml, 'r', encoding='utf-8') as f:
                xml_content = f.read()
                if 'xbmc.python.module' not in xml_content:
                    continue
        except:
            continue
        
        # Look for lib directory
        lib_path = os.path.join(addon_path, 'lib')
        if not os.path.exists(lib_path):
            continue
        
        # Find sources_* directory
        sources_info = None
        
        # Check directly in lib/
        try:
            lib_contents = os.listdir(lib_path)
            for item in lib_contents:
                if item.startswith('sources_'):
                    sources_path = os.path.join(lib_path, item)
                    if os.path.isdir(sources_path):
                        sources_info = {
                            'directory': item,
                            'location': 'lib',
                            'module_name': item.replace('sources_', '')
                        }
                        break
        except:
            pass
        
        # Check in subdirectories (e.g., lib/cocoscrapers/sources_cocoscrapers)
        if not sources_info:
            try:
                lib_contents = os.listdir(lib_path)
                for subdir in lib_contents:
                    if subdir.startswith('.'):
                        continue
                    subdir_path = os.path.join(lib_path, subdir)
                    if not os.path.isdir(subdir_path):
                        continue
                    try:
                        subdir_contents = os.listdir(subdir_path)
                        for item in subdir_contents:
                            if item.startswith('sources_'):
                                sources_path = os.path.join(subdir_path, item)
                                if os.path.isdir(sources_path):
                                    sources_info = {
                                        'directory': item,
                                        'location': 'lib/%s' % subdir,
                                        'module_name': item.replace('sources_', '')
                                    }
                                    break
                        if sources_info:
                            break
                    except:
                        continue
            except:
                pass
        
        # If found, add to list
        if sources_info:
            try:
                addon = xbmcaddon.Addon(addon_dir)
                addon_name = addon.getAddonInfo('name')
                
                scraper_info = {
                    'id': addon_dir,
                    'name': addon_name,
                    'path': addon_path,
                    'lib_path': lib_path,
                    'sources_info': sources_info
                }
                
                detected_scrapers.append(scraper_info)
                log.warning('Detected scraper addon: %s (id: %s, sources: %s/%s)' % 
                           (addon_name, addon_dir, sources_info['location'], sources_info['directory']))
            except Exception as e:
                log.warning('Error loading addon %s: %s' % (addon_dir, str(e)))
    
    return detected_scrapers


def get_enabled_scrapers():
    """
    Get list of enabled scraper addon IDs from settings
    
    Returns:
        list: List of addon IDs that are enabled
    """
    try:
        setting_value = Addon.getSetting('selected_scrapers')
        if setting_value:
            return json.loads(setting_value)
    except Exception as e:
        log.warning('Error reading enabled scrapers setting: %s' % str(e))
    
    return []


def save_enabled_scrapers(addon_ids):
    """
    Save list of enabled scraper addon IDs to settings
    
    Args:
        addon_ids (list): List of addon IDs to enable
    """
    try:
        Addon.setSetting('selected_scrapers', json.dumps(addon_ids))
        log.warning('Saved enabled scrapers: %s' % str(addon_ids))
    except Exception as e:
        log.warning('Error saving enabled scrapers: %s' % str(e))


def get_selected_scrapers():
    """
    Get full info for all enabled scraper addons
    
    Returns:
        list: List of enabled scraper addon dicts
    """
    all_scrapers = detect_scraper_addons()
    enabled_ids = get_enabled_scrapers()
    
    selected = []
    for scraper in all_scrapers:
        if scraper['id'] in enabled_ids:
            selected.append(scraper)
    
    return selected


def load_scraper_modules(scraper_list):
    """
    Load modules from all selected scrapers
    
    Args:
        scraper_list (list): List of scraper info dicts from get_selected_scrapers()
    
    Returns:
        dict: {
            'modules': [(abbr, scraper_name, module), ...],
            'paths_added': [list of sys.path entries added]
        }
    """
    result = {
        'modules': [],
        'paths_added': []
    }
    
    import pkgutil
    
    for scraper in scraper_list:
        try:
            scraper_id = scraper['id']
            scraper_name = scraper['name']
            lib_path = scraper['lib_path']
            sources_info = scraper['sources_info']
            
            # Get 3-letter abbreviation for this scraper
            abbr = get_scraper_abbreviation(scraper_id)
            
            # Build full path to sources directory
            if sources_info['location'] == 'lib':
                sources_path = os.path.join(lib_path, sources_info['directory'])
            else:
                # e.g., lib/cocoscrapers
                sub_path = sources_info['location'].replace('lib/', '')
                sources_path = os.path.join(lib_path, sub_path, sources_info['directory'])
            
            # Check for torrents subdirectory
            torrents_path = os.path.join(sources_path, 'torrents')
            if os.path.isdir(torrents_path):
                sources_path = torrents_path
            
            if not os.path.isdir(sources_path):
                log.warning('Sources path not found: %s' % sources_path)
                continue
            
            # Add lib path to sys.path for imports
            if lib_path not in sys.path:
                sys.path.insert(0, lib_path)
                result['paths_added'].append(lib_path)
            
            # Load all modules from sources directory
            module_count = 0
            for loader, module_name, is_pkg in pkgutil.walk_packages([sources_path]):
                if is_pkg:
                    continue
                try:
                    module = loader.find_module(module_name).load_module(module_name)
                    source_obj = module.source()
                    result['modules'].append((abbr, module_name, source_obj))
                    module_count += 1
                except Exception as e:
                    log.warning('Error loading scraper module %s from %s: %s' % (module_name, scraper_name, str(e)))
            
            log.warning('Loaded %d modules from %s (%s) [%s]' % (module_count, scraper_name, scraper_id, abbr))
            
        except Exception as e:
            log.warning('Error processing scraper addon %s: %s' % (scraper.get('id', 'unknown'), str(e)))
    
    return result


def cleanup_scraper_paths(paths_to_remove):
    """
    Remove added paths from sys.path
    
    Args:
        paths_to_remove (list): List of paths to remove from sys.path
    """
    for path in paths_to_remove:
        try:
            if path in sys.path:
                sys.path.remove(path)
                log.warning('Removed path from sys.path: %s' % path)
        except Exception as e:
            log.warning('Error removing path from sys.path: %s' % str(e))
