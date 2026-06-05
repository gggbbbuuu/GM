# -*- coding: utf-8 -*-
"""
Scraper Addon Selector UI
Allows users to select multiple scraper addons to use
"""

import xbmcgui
import xbmcaddon
from resources.modules import scraper_manager, log

Addon = xbmcaddon.Addon('plugin.video.shadow')


def show_scraper_selector():
    """
    Show a multi-select dialog for available scraper addons
    """
    try:
        # Detect all available scrapers
        available_scrapers = scraper_manager.detect_scraper_addons()
        
        if not available_scrapers:
            xbmcgui.Dialog().ok(
                'No Scraper Addons Found',
                'No scraper addons detected. Install script.module.cocoscrapers or plugin.program.taz19scrapers'
            )
            return False
        
        # Get currently selected scrapers
        enabled_ids = scraper_manager.get_enabled_scrapers()
        
        # Build list of items with checkmarks
        items = []
        item_ids = []
        
        for scraper in available_scrapers:
            scraper_id = scraper['id']
            scraper_name = scraper['name']
            sources_info = scraper['sources_info']
            
            # Create display name
            display_name = '%s [%s]' % (scraper_name, sources_info['directory'])
            
            # Add checkmark if enabled
            if scraper_id in enabled_ids:
                display_name = '[✓] %s' % display_name
            else:
                display_name = '[ ] %s' % display_name
            
            items.append(display_name)
            item_ids.append(scraper_id)
            
            log.warning('Scraper option: %s (id: %s)' % (display_name, scraper_id))
        
        # Show multi-select dialog
        dialog = xbmcgui.Dialog()
        selected_indices = dialog.multiselect(
            'Select Scraper Addons',
            items
        )
        
        if selected_indices is not None:  # Not cancelled
            # Build list of selected addon IDs
            selected_ids = [item_ids[i] for i in selected_indices]
            
            # Save selection
            scraper_manager.save_enabled_scrapers(selected_ids)
            
            # Show confirmation
            if selected_ids:
                message = 'Selected %d scraper addon(s):\n' % len(selected_ids)
                for addon_id in selected_ids:
                    addon = xbmcaddon.Addon(addon_id)
                    message += '• %s\n' % addon.getAddonInfo('name')
                
                xbmcgui.Dialog().ok('Scrapers Configured', message)
                log.warning('Scraper selection saved: %s' % str(selected_ids))
            else:
                xbmcgui.Dialog().ok('Scrapers Disabled', 'No scrapers selected. External scraper support disabled.')
                log.warning('Scraper selection cleared')
            
            return True
        
        return False
    
    except Exception as e:
        log.warning('Error in scraper selector: %s' % str(e))
        xbmcgui.Dialog().ok('Error', 'Error configuring scrapers: %s' % str(e))
        return False
