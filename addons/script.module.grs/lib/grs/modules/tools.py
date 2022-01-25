# -*- coding: utf-8 -*-

import six, re

def clear_Title(txt):
    txt = six.ensure_str(txt, errors='ignore')
    txt = re.sub('<.+?>', '', txt)
    txt = txt.replace('Δες το ', '').replace(' online', '')
    txt = txt.replace("&quot;", "\"").replace('()','').replace("&#038;", "&").replace('&#8211;',':').replace('\n',' ')
    txt = txt.replace("&amp;", "&").replace('&#8217;',"'").replace('&#039;',':').replace('&#;','\'')
    txt = txt.replace("&#38;", "&").replace('&#8221;','"').replace('&#8216;','"').replace('&#160;','')
    txt = txt.replace("&nbsp;", "").replace('&#8220;','"').replace('&#8216;','"').replace('\t',' ').replace('&#215;','x')
    return txt