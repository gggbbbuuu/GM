# -*- coding: utf-8 -*-

'''
    Soma FM Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from tulip import control, client
import html2text


def description(text):

    return control.dialog.textviewer('SomaFM', text)


def info_cm():

    control.execute('Action(Info)')


def history(url):

    html = client.request(url)
    mid = client.parseDOM(html, 'div', attrs={'id': 'midcontent'})[0]

    h2t = html2text.HTML2Text()
    h2t.ignore_links = True
    h2t.ignore_images = True
    h2t.ignore_emphasis = True
    h2t.body_width = 300

    text = h2t.handle(mid)

    return control.dialog.textviewer('SomaFM', text)
