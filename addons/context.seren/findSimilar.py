import sys, xbmc, json

try:
    from urlparse import parse_qsl, unquote
except:
    from urllib.parse import parse_qsl, unquote

if __name__ == '__main__':

    item = sys.listitem

    path = item.getPath()
    plugin = 'plugin://plugin.video.seren'
    path = path.split(plugin, 1)

    params = dict(parse_qsl(path[1].replace('?', '')))
    action_args = json.loads(unquote(params.get('action_args')))
    if action_args['mediatype'] == 'tvshow':
        xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.video.seren/?action=showsRelated&action_args=%s)'
                        % action_args['trakt_id'])
    else:
        xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.video.seren/?action=moviesRelated&action_args=%s)'
                        % action_args['trakt_id'])
