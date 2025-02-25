# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re, unicodedata
from shutil import copy
from os.path import splitext, exists, split as os_split
from resources.lib import subtitlesgr, xsubstv, podnapisi, vipsubs
from tulip.fuzzywuzzy.fuzz import ratio
from tulip import control
from tulip.compat import urlencode, py3_dec, concurrent_futures
from tulip.log import log_debug


if control.condVisibility('Player.HasVideo'):
    infolabel_prefix = 'VideoPlayer'
else:
    infolabel_prefix = 'ListItem'


class Search:

    def __init__(self, syshandle, sysaddon, langs, action):

        self.list = []
        self.query = None
        self.syshandle = syshandle
        self.sysaddon = sysaddon
        self.langs = langs
        self.action = action

    def run(self, query=None):

        if 'Greek' not in str(self.langs).split(','):

            control.directory(self.syshandle)
            control.infoDialog(control.lang(30002))

            return

        dup_removal = False

        if not query:

            title = match_title = control.infoLabel('{0}.Title'.format(infolabel_prefix))

            with concurrent_futures.ThreadPoolExecutor(5) as executor:

                if re.search(r'[^\x00-\x7F]+', title) is not None:

                    title = control.infoLabel('{0}.OriginalTitle'.format(infolabel_prefix))

                title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')
                title = py3_dec(title)
                year = control.infoLabel('{0}.Year'.format(infolabel_prefix))
                tvshowtitle = control.infoLabel('{0}.TVshowtitle'.format(infolabel_prefix))
                season = control.infoLabel('{0}.Season'.format(infolabel_prefix))

                if len(season) == 1:

                    season = '0' + season

                episode = control.infoLabel('{0}.Episode'.format(infolabel_prefix))

                if len(episode) == 1:
                    episode = '0' + episode

                if 's' in episode.lower():
                    season, episode = '0', episode[-1:]

                if tvshowtitle != '':  # episode

                    title_query = '{0} {1}'.format(tvshowtitle, title)
                    season_episode_query = '{0} S{1} E{2}'.format(tvshowtitle, season, episode)
                    season_episode_query_nospace = '{0} S{1}E{2}'.format(tvshowtitle, season, episode)

                    threads = [
                        executor.submit(self.subtitlesgr, season_episode_query_nospace),
                        executor.submit(self.xsubstv, season_episode_query),
                        executor.submit(self.podnapisi, season_episode_query),
                        executor.submit(self.vipsubs, season_episode_query)
                    ]

                    dup_removal = True

                    log_debug('Dual query used for subtitles search: ' + title_query + ' / ' + season_episode_query)

                    if control.setting('queries') == 'true':

                        threads.extend(
                            [
                                executor.submit(self.subtitlesgr, title_query),
                                executor.submit(self.vipsubs, title_query),
                                executor.submit(self.podnapisi, title_query),
                                executor.submit(self.subtitlesgr, season_episode_query)
                            ]
                        )

                elif year != '':  # movie

                    query = '{0} ({1})'.format(title, year)

                    threads = [
                        executor.submit(self.subtitlesgr, query), executor.submit(self.xsubstv, query),
                        executor.submit(self.vipsubs, query), executor.submit(self.podnapisi, query)
                    ]

                else:  # file

                    query, year = control.cleanmovietitle(title)

                    if year != '':

                        query = '{0} ({1})'.format(query, year)

                    threads = [
                        executor.submit(self.subtitlesgr, query), executor.submit(self.xsubstv, query),
                        executor.submit(self.vipsubs, query), executor.submit(self.podnapisi, query)
                    ]

                for future in concurrent_futures.as_completed(threads):

                    item = future.result()

                    if not item:
                        continue

                    self.list.extend(item)

                if not dup_removal:

                    log_debug('Query used for subtitles search: ' + query)

                self.query = query

                self.query = py3_dec(self.query)

        else:  # Manual query

            with concurrent_futures.ThreadPoolExecutor(5) as executor:

                query = match_title = py3_dec(query)

                threads = [
                    executor.submit(self.subtitlesgr, query), executor.submit(self.xsubstv, query),
                    executor.submit(self.vipsubs, query), executor.submit(self.podnapisi, query)
                ]

                for future in concurrent_futures.as_completed(threads):

                    item = future.result()

                    if not item:
                        continue

                    self.list.extend(item)

        if len(self.list) == 0:

            control.directory(self.syshandle)

            return

        f = []

        # noinspection PyUnresolvedReferences
        f += [i for i in self.list if i['source'] == 'xsubstv']
        f += [i for i in self.list if i['source'] == 'subtitlesgr']
        f += [i for i in self.list if i['source'] == 'podnapisi']
        f += [i for i in self.list if i['source'] == 'vipsubs']

        self.list = f

        if dup_removal:

            self.list = [dict(t) for t in {tuple(d.items()) for d in self.list}]

        for i in self.list:

            try:

                if i['source'] == 'xsubstv':
                    i['name'] = u'[xsubstv] {0}'.format(i['name'])
                elif i['source'] == 'podnapisi':
                    i['name'] = u'[podnapisi] {0}'.format(i['name'])
                elif i['source'] == 'vipsubs':
                    i['name'] = u'[vipsubs] {0}'.format(i['name'])

            except Exception:

                pass

        if control.setting('sorting') == '1':
            key = 'source'
        elif control.setting('sorting') == '2':
            key = 'downloads'
        elif control.setting('sorting') == '3':
            key = 'rating'
        else:
            key = 'title'

        self.list = sorted(self.list, key=lambda k: k[key].lower(), reverse=control.setting('sorting') in ['1', '2', '3'])

        for i in self.list:

            u = {'action': 'download', 'url': i['url'], 'source': i['source']}
            u = '{0}?{1}'.format(self.sysaddon, urlencode(u))
            item = control.item(label='Greek', label2=i['name'])
            item.setArt({'icon': str(i['rating'])[:1], 'thumb': 'el'})
            if ratio(splitext(i['title'].lower())[0], splitext(match_title)[0]) >= int(control.setting('sync_probability')):
                item.setProperty('sync', 'true')
            else:
                item.setProperty('sync', 'false')
            item.setProperty('hearing_imp', 'false')

            control.addItem(handle=self.syshandle, url=u, listitem=item, isFolder=False)

        control.directory(self.syshandle)

    def subtitlesgr(self, query=None):

        if not query:

            query = self.query

        try:

            if control.setting('subtitles') == 'false':
                raise TypeError

            result = subtitlesgr.Subtitlesgr().get(query)

            return result

        except TypeError:

            pass

    def podnapisi(self, query=None):

        if not query:

            query = self.query

        try:

            if control.setting('podnapisi') == 'false':
                raise TypeError

            result = podnapisi.Podnapisi().get(query)

            return result

        except TypeError:

            pass

    def vipsubs(self, query=None):

        if not query:

            query = self.query

        try:

            if control.setting('vipsubs') == 'false':
                raise TypeError

            result = vipsubs.Vipsubs().get(query)

            return result

        except TypeError:

            pass

    def xsubstv(self, query=None):

        if not query:

            query = self.query

        try:

            if control.setting('xsubs') == 'false':
                raise TypeError

            result = xsubstv.Xsubstv().get(query)

            self.list.extend(result)

        except TypeError:

            pass


class Download:

    def __init__(self, syshandle, sysaddon):

        self.syshandle = syshandle
        self.sysaddon = sysaddon

    # noinspection PyUnboundLocalVariable
    def run(self, url, source):

        log_debug('Source selected: {0}'.format(source))

        path = control.join(control.dataPath, 'temp')

        try:

            path = path.decode('utf-8')

        except Exception:

            pass

        control.deleteDir(control.join(path, ''), force=True)
        control.makeFile(control.dataPath)
        control.makeFile(path)

        if control.setting('keep_subs') == 'true' or control.setting('keep_zips') == 'true':

            if not control.get_info_label('ListItem.Path').startswith('plugin://') and control.setting('destination') == '0':
                output_path = control.get_info_label('Container.FolderPath')
            elif control.setting('output_folder').startswith('special://'):
                output_path = control.transPath(control.setting('output_folder'))
            else:
                output_path = control.setting('output_folder')

            if not exists(output_path):
                control.makeFile(output_path)

        if source == 'subtitlesgr':

            subtitle = subtitlesgr.Subtitlesgr().download(path, url)

        elif source == 'xsubstv':

            subtitle = xsubstv.Xsubstv().download(path, url)

        elif source == 'podnapisi':

            subtitle = podnapisi.Podnapisi().download(path, url)

        elif source == 'vipsubs':

            subtitle = vipsubs.Vipsubs().download(path, url)

        else:

            subtitle = None

        if subtitle is not None:

            if control.setting('keep_subs') == 'true':

                # noinspection PyUnboundLocalVariable
                try:
                    if control.setting('destination') in ['0', '2']:
                        if control.infoLabel('{0}.Title'.format(infolabel_prefix)).startswith('plugin://'):
                            copy(subtitle, control.join(output_path, os_split(subtitle)[1]))
                            log_debug('Item currently selected is not a local file, cannot save subtitle next to it')
                        else:
                            output_filename = control.join(
                                    output_path, ''.join(
                                        [
                                            splitext(control.infoLabel('ListItem.FileName'))[0],
                                            splitext(os_split(subtitle)[1])[1]
                                        ]
                                    )
                                )
                            if exists(output_filename):
                                yesno = control.yesnoDialog(control.lang(30015))
                                if yesno:
                                    copy(subtitle, output_filename)
                            else:
                                copy(subtitle, output_filename)
                            if control.setting('destination') == '2':
                                if control.setting('output_folder').startswith('special://'):
                                    output_path = control.transPath(control.setting('output_folder'))
                                else:
                                    output_path = control.setting('output_folder')
                                copy(subtitle, control.join(output_path, os_split(subtitle)[1]))
                    else:
                        copy(subtitle, control.join(output_path, os_split(subtitle)[1]))
                    control.infoDialog(control.lang(30008))
                except Exception:
                    control.infoDialog(control.lang(30013))

            item = control.item(label=subtitle)
            control.addItem(handle=self.syshandle, url=subtitle, listitem=item, isFolder=False)

        control.directory(self.syshandle)
