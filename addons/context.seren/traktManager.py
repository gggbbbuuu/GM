import sys, xbmc, json

try:
    from urlparse import parse_qsl
    from urllib import quote
except:
    from urllib.parse import parse_qsl, quote

if __name__ == '__main__':
    item = sys.listitem
    message = item.getLabel()
    path = item.getPath()
    args = path.split('?')

    params = dict(parse_qsl(args[1]))

    path = 'RunPlugin(plugin://plugin.video.seren/?action=traktManager&action_args={})' \
           ''.format(quote(params.get('action_args')))
    xbmc.executebuiltin(path)
