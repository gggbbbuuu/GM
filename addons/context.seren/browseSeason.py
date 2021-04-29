import sys, xbmc, json

try:
    from urlparse import parse_qsl
    from urllib import quote, unquote
except:
    from urllib.parse import parse_qsl, quote, unquote

if __name__ == '__main__':

    item = sys.listitem

    path = item.getPath()
    args = path.split('?', 1)
    params = dict(parse_qsl(unquote(args[1])))
    action = params.get('action')
    action_args = params.get('action_args')
    action_args = json.loads(unquote(action_args))
    action_args['media_type'] = 'season'
    action_args.pop('season', '')
    action_args['trakt_id'] = action_args['trakt_season_id']
    action_args.pop('trakt_season_id', '')

    path = 'plugin://plugin.video.seren/?action=seasonEpisodes&action_args={}'.format(quote(json.dumps(action_args)))

    xbmc.executebuiltin('ActivateWindow(Videos,%s)' % path)
