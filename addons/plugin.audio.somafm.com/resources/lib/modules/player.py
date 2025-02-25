# -*- coding: utf-8 -*-

'''
    Soma FM Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from tulip import directory, control, client
import re
from ast import literal_eval
from random import choice


ttz = 'MP3 320k'
tfs = 'MP3 256k'
ont = 'MP3 192k'
ote = 'MP3 128k'

aac1 = 'AAC 128k'
aac2 = 'AAC 64k'
aac3 = 'AAC 32k'


def selector(qofs, lofs, quality=ote):

    idx = qofs.index(quality)
    stream = lofs.pop(idx)

    return stream


def resolver(url):

    return choice(re.findall(r'File1=([\w:\./-]*)', url))


def player(url):

    qofs = []

    lofs = literal_eval(url)

    print(lofs)

    for item in lofs:

        if '320' in item:
            item = ttz
        elif '256' in item:
            item = tfs
        elif '192' in item:
            item = ont
        elif '130' in item:
            item = aac1
        elif '64' in item:
            item = aac2
        elif '32' in item:
            item = aac3
        else:
            item = ote

        qofs.append(item)

    if control.setting('quality_selector') == '0':

        choice = control.selectDialog(heading='Select quality', list=qofs)

        if choice <= len(lofs) and not choice == -1:

            link = lofs.pop(choice)

            stream = resolver(link)

            directory.resolve(stream)

        else:

            control.execute('Playlist.Clear')
            control.sleep(100)
            control.execute('Dialog.Close(all)')

    elif control.setting('quality_selector') == '1':

        stream = client.request(selector(qofs, lofs))
        stream = resolver(stream)
        directory.resolve(stream)

    elif control.setting('quality_selector') == '2':

        if 'MP3 320k' in qofs:
            stream = client.request(selector(qofs, lofs, ttz))
        elif 'MP3 256k' in qofs:
            stream = client.request(selector(qofs, lofs, tfs))
        elif 'MP3 192k' in qofs:
            stream = client.request(selector(qofs, lofs, ont))
        else:
            stream = client.request(selector(qofs, lofs))

        stream = resolver(stream)
        directory.resolve(stream)

    elif control.setting('quality_selector') == '3':

        stream = client.request(selector(qofs, lofs))
        stream = resolver(stream)
        directory.resolve(stream)

    elif control.setting('quality_selector') == '4':

        if 'AAC 128k' in qofs:
            stream = client.request(selector(qofs, lofs, aac1))
        elif 'AAC 64k' in qofs:
            stream = client.request(selector(qofs, lofs, aac2))
        elif 'AAC 32k' in qofs:
            stream = client.request(selector(qofs, lofs, aac3))
        else:
            stream = selector(qofs, lofs)

        stream = resolver(stream)
        directory.resolve(stream)

    elif control.setting('quality_selector') == '5':

        if 'AAC 128k' in qofs:
            stream = client.request(selector(qofs, lofs, aac3))
        elif 'AAC 64k' in qofs:
            stream = client.request(selector(qofs, lofs, aac2))
        elif 'AAC 32k' in qofs:
            stream = client.request(selector(qofs, lofs, aac1))
        else:
            stream = selector(qofs, lofs)

        stream = resolver(stream)
        directory.resolve(stream)

    else:

        selector(qofs, lofs)