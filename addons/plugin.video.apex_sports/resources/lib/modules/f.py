from resources.lib.modules.log_utils import log
import os ,re ,urllib ,urllib2 #line:2
import requests #line:3
import xbmc ,xbmcaddon ,xbmcgui ,xbmcvfs #line:4
import base64 #line:5
addonInfo =xbmcaddon .Addon ().getAddonInfo #line:7
file_open =xbmcvfs .File #line:8
file_delete =xbmcvfs .delete #line:9
DATAPATH =xbmc .translatePath (addonInfo ('profile')).decode ('utf-8')#line:10
control =xbmcgui .ControlImage #line:12
dialog =xbmcgui .WindowDialog ()#line:13
KEYBOARD =xbmc .Keyboard #line:14
import string #line:16
STANDARD_ALPHABET ='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='#line:18
CUSTOM_ALPHABET ='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/='#line:19
ENCODE_TRANS =string .maketrans (STANDARD_ALPHABET ,CUSTOM_ALPHABET )#line:20
DECODE_TRANS =string .maketrans (CUSTOM_ALPHABET ,STANDARD_ALPHABET )#line:21
def decode2 (OO000OOO0O0O0O0O0 ):#line:23
  return base64 .b64decode (OO000OOO0O0O0O0O0 .translate (DECODE_TRANS ))#line:24
def getkey (OOOO00OO0OOO0O000 ):#line:26
    class O000O000O00000OOO (object ):#line:27
        def __init__ (OOOO00000O000OOOO ,OO0O00000000000OO ):#line:29
            OOOO00000O000OOOO .data =OO0O00000000000OO #line:30
            OOOO00000O000OOOO .funcion =''#line:31
            OOOO00000O000OOOO .lista =[]#line:32
            OOOO00000O000OOOO .l1l1ll ,OOOO00000O000OOOO .msg =OOOO00000O000OOOO .l11ll1 ()#line:33
            if OOOO00000O000OOOO .l1l1ll :#line:34
                O000O0O0000O0O0OO =re .compile ("""(%s\\(['"]([^'"]*)['"],\\s*['"]([^'"]*)['"]\\))"""%OOOO00000O000OOOO .funcion ).findall (OOOO00000O000OOOO .data )#line:36
                for O0O00O0O0O0OOO000 ,O0OO000O000O00OOO in enumerate (O000O0O0000O0O0OO ):#line:37
                    OO0000O0OOO00O00O =OOOO00000O000OOOO .unhex (O0OO000O000O00OOO [2 ])if O0OO000O000O00OOO [2 ][:2 ]=='\\x'else O0OO000O000O00OOO [2 ]#line:38
                    OO00OO000000OO0OO =OOOO00000O000OOOO .l1ll11 (int (O0OO000O000O00OOO [1 ],16 ),OO0000O0OOO00O00O )#line:39
                    if "'"not in OO00OO000000OO0OO :#line:40
                        OOOO00000O000OOOO .data =OOOO00000O000OOOO .data .replace (O0OO000O000O00OOO [0 ],"'"+OO00OO000000OO0OO +"'")#line:41
                    elif '"'not in OO00OO000000OO0OO :#line:42
                        OOOO00000O000OOOO .data =OOOO00000O000OOOO .data .replace (O0OO000O000O00OOO [0 ],'"'+OO00OO000000OO0OO +'"')#line:43
                    else :#line:44
                        return #line:45
                O000O0O0000O0O0OO =re .compile ("""(%s\\(\\\\['"](.*?)\\\\['"],\\s*\\\\['"](.*?)\\\\['"]\\))"""%OOOO00000O000OOOO .funcion ).findall (OOOO00000O000OOOO .data )#line:46
                for O0O00O0O0O0OOO000 ,O0OO000O000O00OOO in enumerate (O000O0O0000O0O0OO ):#line:48
                    OO0000O0OOO00O00O =OOOO00000O000OOOO .unhex (O0OO000O000O00OOO [2 ])if O0OO000O000O00OOO [2 ][:2 ]=='\\x'else O0OO000O000O00OOO [2 ]#line:49
                    OO00OO000000OO0OO =OOOO00000O000OOOO .l1ll11 (int (O0OO000O000O00OOO [1 ],16 ),OO0000O0OOO00O00O )#line:50
                    if "'"not in OO00OO000000OO0OO :#line:51
                        OOOO00000O000OOOO .data =OOOO00000O000OOOO .data .replace (O0OO000O000O00OOO [0 ],"\\'"+OO00OO000000OO0OO +"\\'")#line:52
                    elif '"'not in OO00OO000000OO0OO :#line:53
                        OOOO00000O000OOOO .data =OOOO00000O000OOOO .data .replace (O0OO000O000O00OOO [0 ],'\\"'+OO00OO000000OO0OO +'\\"')#line:54
                    else :#line:55
                        return #line:56
                O000O0O0000O0O0OO =re .compile ("""(%s\\(['"]([^'"]*)['"]\\))"""%OOOO00000O000OOOO .funcion ).findall (OOOO00000O000OOOO .data )#line:59
                for O0O00O0O0O0OOO000 ,O0OO000O000O00OOO in enumerate (O000O0O0000O0O0OO ):#line:61
                    OO00OO000000OO0OO =OOOO00000O000OOOO .l1ll11 (int (OOOO00000O000OOOO .unhex (O0OO000O000O00OOO [1 ]),16 ),'')#line:63
                    if "'"not in OO00OO000000OO0OO :#line:64
                        OOOO00000O000OOOO .data =OOOO00000O000OOOO .data .replace (O0OO000O000O00OOO [0 ],"'"+OO00OO000000OO0OO +"'")#line:65
                    elif '"'not in OO00OO000000OO0OO :#line:66
                        OOOO00000O000OOOO .data =OOOO00000O000OOOO .data .replace (O0OO000O000O00OOO [0 ],'"'+OO00OO000000OO0OO +'"')#line:67
                    else :#line:68
                        return #line:69
                O000O0O0000O0O0OO =re .compile ("""(%s\\(\\\\['"](.*?)\\\\['"]\\))"""%OOOO00000O000OOOO .funcion ).findall (OOOO00000O000OOOO .data )#line:70
                for O0O00O0O0O0OOO000 ,O0OO000O000O00OOO in enumerate (O000O0O0000O0O0OO ):#line:72
                    OO00OO000000OO0OO =OOOO00000O000OOOO .l1ll11 (int (O0OO000O000O00OOO [1 ],16 ),'')#line:73
                    if "'"not in OO00OO000000OO0OO :#line:74
                        OOOO00000O000OOOO .data =OOOO00000O000OOOO .data .replace (O0OO000O000O00OOO [0 ],"\\'"+OO00OO000000OO0OO +"\\'")#line:75
                    elif '"'not in OO00OO000000OO0OO :#line:76
                        OOOO00000O000OOOO .data =OOOO00000O000OOOO .data .replace (O0OO000O000O00OOO [0 ],'\\"'+OO00OO000000OO0OO +'\\"')#line:77
                    else :#line:78
                        return #line:79
        def l11ll1 (O0O00OO0000OOOOO0 ):#line:81
            O0OOO0O0OO000O00O =re .search ('var (\\w*)\\s*=\\s*\\[(.*?)\\];',O0O00OO0000OOOOO0 .data )#line:82
            if not O0OOO0O0OO000O00O :#line:83
                return (False ,'')#line:84
            OOO0O0OO0O0O0O0O0 =O0OOO0O0OO000O00O .group (1 )#line:85
            O0O00OO0000OOOOO0 .lista =O0OOO0O0OO000O00O .group (2 ).split (',')#line:86
            for O000O000O0OO0OO0O ,OOO000O00000O0OOO in enumerate (O0O00OO0000OOOOO0 .lista ):#line:87
                O0O00OO0000OOOOO0 .lista [O000O000O0OO0OO0O ]=OOO000O00000O0OOO .strip ()[1 :-1 ]#line:88
            if O0O00OO0000OOOOO0 .lista [0 ][:2 ]=='\\x':#line:90
                for O000O000O0OO0OO0O ,OOO000O00000O0OOO in enumerate (O0O00OO0000OOOOO0 .lista ):#line:91
                    O0O00OO0000OOOOO0 .lista [O000O000O0OO0OO0O ]=O0O00OO0000OOOOO0 .unhex (OOO000O00000O0OOO )#line:92
            O0O00OO0000OOOOO0 .data =O0O00OO0000OOOOO0 .data .replace (O0OOO0O0OO000O00O .group (0 ),'')#line:94
            O0OOO0O0OO000O00O =re .search ('\\(function\\(.*?}\\(%s,\\s*([^\\)]*)\\)\\);'%OOO0O0OO0O0O0O0O0 ,O0O00OO0000OOOOO0 .data ,flags =re .DOTALL )#line:95
            if not O0OOO0O0OO000O00O :#line:96
                return (False ,'')#line:97
            O000OO00O0OOO0000 =O0OOO0O0OO000O00O .group (1 )#line:98
            OOOO00O0OOO00000O =eval (O000OO00O0OOO0000 )#line:103
            O0O00OO0000OOOOO0 .data =O0O00OO0000OOOOO0 .data .replace (O0OOO0O0OO000O00O .group (0 ),'')#line:105
            for O0OO000OO0O00OO00 in range (OOOO00O0OOO00000O ):#line:106
                O0O00OO0000OOOOO0 .lista .append (O0O00OO0000OOOOO0 .lista .pop (0 ))#line:107
            O0OOO0000OOOOOO0O ="""var (\w*)\s*=\s*function\s*\(\s*[0-9a-fA-F]+,\s*[0-9a-fA-F]+\s*\)\s*{\s*[0-9a-fA-F]+"""#line:110
            O000O000O000OOOOO ="""var (\w*)\s*=\s*function\s*\(\s*_0[xX][0-9a-fA-F]+\s*,\s*_0[xX][0-9a-fA-F]+"""#line:111
            O0OOO0O0OO000O00O =re .search (O0OOO0000OOOOOO0O ,O0O00OO0000OOOOO0 .data )#line:112
            OOO000OO00OO000OO =re .search (O000O000O000OOOOO ,O0O00OO0000OOOOO0 .data )#line:113
            if not O0OOO0O0OO000O00O and not OOO000OO00OO000OO :#line:116
              return (False ,'')#line:117
            else :#line:118
              O0OOO0O0OO000O00O =O0OOO0O0OO000O00O if O0OOO0O0OO000O00O else OOO000OO00OO000OO #line:119
            O0O00OO0000OOOOO0 .funcion =O0OOO0O0OO000O00O .group (1 ).strip ()#line:126
            O0O00OO0000OOOOO0 .data =O0O00OO0000OOOOO0 .data .replace (O0OOO0O0OO000O00O .group (0 ),'')#line:127
            return (True ,'')#line:129
        def l1ll11 (OO00OO0O000OO0O0O ,O0O00OO00O000O00O ,s =''):#line:131
            O0OO0OO000O0000OO =str (OO00OO0O000OO0O0O .lista [O0O00OO00O000O00O ])#line:132
            O0OO0OO000O0000OO =decode2 (O0OO0OO000O0000OO )#line:133
            O0OO0O0OOO00O00OO =''#line:136
            for OOO0O0O000O0O0O0O in range (len (O0OO0OO000O0000OO )):#line:137
                O0OO0O0OOO00O00OO +='%'+('00'+hex (ord (O0OO0OO000O0000OO [OOO0O0O000O0O0O0O ]))[2 :])[-2 :]#line:138
            else :#line:142
                O0OO0OO000O0000OO =unicode (urllib .unquote (O0OO0O0OOO00O00OO ),'utf8')#line:143
            if s =='':#line:144
                return O0OO0OO000O0000OO #line:145
            else :#line:146
                OO00OOO0O0O000O00 =list (range (256 ))#line:147
                O0O0O0000O0O0O0OO =0 #line:148
                OOO00000O0O0OOOO0 =''#line:149
                for OOO0O0O000O0O0O0O in range (256 ):#line:150
                    O0O0O0000O0O0O0OO =(O0O0O0000O0O0O0OO +OO00OOO0O0O000O00 [OOO0O0O000O0O0O0O ]+ord (s [(OOO0O0O000O0O0O0O %len (s ))]))%256 #line:151
                    O0O00O000O0O0OO0O =OO00OOO0O0O000O00 [OOO0O0O000O0O0O0O ]#line:152
                    OO00OOO0O0O000O00 [OOO0O0O000O0O0O0O ]=OO00OOO0O0O000O00 [O0O0O0000O0O0O0OO ]#line:153
                    OO00OOO0O0O000O00 [O0O0O0000O0O0O0OO ]=O0O00O000O0O0OO0O #line:154
                OOO0O0OOO0OOO0O0O =0 #line:156
                O0O0O0000O0O0O0OO =0 #line:157
                for OOO0O0O000O0O0O0O in range (len (O0OO0OO000O0000OO )):#line:158
                    OOO0O0OOO0OOO0O0O =(OOO0O0OOO0OOO0O0O +1 )%256 #line:159
                    O0O0O0000O0O0O0OO =(O0O0O0000O0O0O0OO +OO00OOO0O0O000O00 [OOO0O0OOO0OOO0O0O ])%256 #line:160
                    O0O00O000O0O0OO0O =OO00OOO0O0O000O00 [OOO0O0OOO0OOO0O0O ]#line:161
                    OO00OOO0O0O000O00 [OOO0O0OOO0OOO0O0O ]=OO00OOO0O0O000O00 [O0O0O0000O0O0O0OO ]#line:162
                    OO00OOO0O0O000O00 [O0O0O0000O0O0O0OO ]=O0O00O000O0O0OO0O #line:163
                    OOO00000O0O0OOOO0 +=unichr (ord (O0OO0OO000O0000OO [OOO0O0O000O0O0O0O ])^OO00OOO0O0O000O00 [((OO00OOO0O0O000O00 [OOO0O0OOO0OOO0O0O ]+OO00OOO0O0O000O00 [O0O0O0000O0O0O0OO ])%256 )])#line:164
                return OOO00000O0O0OOOO0 .encode ('utf8')#line:168
        def unhex (O0OO000O0OO0OOO0O ,OOOOO0O0O00OOOO0O ):#line:170
            return re .sub ('\\\\x[a-f0-9][a-f0-9]',lambda OO0O0OOO000000000 :OO0O0OOO000000000 .group ()[2 :].decode ('hex'),OOOOO0O0O00OOOO0O )#line:171
    OOO00OO0OO00OOOOO =O000O000O00000OOO (OOOO00OO0OOO0O000 )#line:172
    O0O0OO00000000OO0 =O000O000O00000OOO (OOO00OO0OO00OOOOO .data )#line:173
    def O000O0000O000O0O0 (OO0O00OOO000O00OO ):#line:174
        return re .sub ('\\\\x[a-f0-9][a-f0-9]',lambda OO00000O000OOOO0O :OO00000O000OOOO0O .group ()[2 :].decode ('hex'),OO0O00OOO000O00OO )#line:175
    return O000O0000O000O0O0 (O0O0OO00000000OO0 .data )#line:176
