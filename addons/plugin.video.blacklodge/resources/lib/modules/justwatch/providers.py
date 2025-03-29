# -*- coding: utf-8 -*-

from resources.lib.modules import control

NETFLIX_ENABLED = (control.condVisibility('System.HasAddon(plugin.video.netflix)') and control.setting('netflix') == 'true')
PRIME_ENABLED = (control.condVisibility('System.HasAddon(plugin.video.amazon-test)') and control.setting('prime') == 'true')
HBO_ENABLED = (control.condVisibility('System.HasAddon(slyguy.hbo.max)') and control.setting('hbo.max') == 'true')
MAX_ENABLED = (control.condVisibility('System.HasAddon(slyguy.max)') and control.setting('max') == 'true')
DISNEY_ENABLED = (control.condVisibility('System.HasAddon(slyguy.disney.plus)') and control.setting('disney.plus') == 'true')
IPLAYER_ENABLED = (control.condVisibility('System.HasAddon(plugin.video.iplayerwww)') and control.setting('iplayer') == 'true')
CURSTREAM_ENABLED = (any((control.condVisibility('System.HasAddon(slyguy.curiositystream)'), control.condVisibility('System.HasAddon(plugin.video.curiositystream)'))) and control.setting('curstream') == 'true')
HULU_ENABLED = (control.condVisibility('System.HasAddon(slyguy.hulu)') and control.setting('hulu') == 'true')
ITV_ENABLED = (control.condVisibility('System.HasAddon(plugin.video.viwx)') and control.setting('itv') == 'true')
PARAMOUNT_ENABLED = (control.condVisibility('System.HasAddon(slyguy.paramount.plus)') and control.setting('paramount') == 'true')
CRACKLE_ENABLED = (control.condVisibility('System.HasAddon(plugin.video.crackle)') and control.setting('crackle') == 'true')
TUBI_ENABLED = (any((control.condVisibility('System.HasAddon(plugin.video.tubi.m7)'), control.condVisibility('System.HasAddon(plugin.video.tubitv)'))) and control.setting('tubi') == 'true')
UKTVPLAY_ENABLED = (control.condVisibility('System.HasAddon(plugin.video.catchuptvandmore)') and control.setting('uktvplay') == 'true')
PLUTO_ENABLED = (control.condVisibility('System.HasAddon(plugin.video.plutotv)') and control.setting('plutotv') == 'true')

SCRAPER_INIT = any(e for e in [NETFLIX_ENABLED, PRIME_ENABLED, HBO_ENABLED, MAX_ENABLED, DISNEY_ENABLED, IPLAYER_ENABLED, CURSTREAM_ENABLED, HULU_ENABLED, ITV_ENABLED,
                               PARAMOUNT_ENABLED, CRACKLE_ENABLED, TUBI_ENABLED, UKTVPLAY_ENABLED, PLUTO_ENABLED])


def enabled_services():
    services = [
        ('BBC iPlayer', '38', IPLAYER_ENABLED),
        ('Crackle', '12', CRACKLE_ENABLED),
        ('Curiosity Stream', '190', CURSTREAM_ENABLED),
        ('Disney+', '337', DISNEY_ENABLED),
        ('HBO Max', '616|384|27|425', HBO_ENABLED),
        ('Hulu', '15', HULU_ENABLED),
        ('ITV Hub', '41', ITV_ENABLED),
        ('MAX', '1899', MAX_ENABLED),
        ('Netflix', '8|175|1796', NETFLIX_ENABLED),
        ('Paramount+', '531', PARAMOUNT_ENABLED),
        ('Pluto TV', '300', PLUTO_ENABLED),
        ('Prime Video', '9|119|613|582', PRIME_ENABLED),
        ('Tubi TV', '73', TUBI_ENABLED),
        ('UKTV Play', '137', UKTVPLAY_ENABLED)
    ]
    return [s for s in services if s[2]]
