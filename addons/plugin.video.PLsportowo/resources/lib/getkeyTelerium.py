import re ,sys #line:2
import base64 #line:4
PY3 =False #line:6
if sys .version_info [0 ]>=3 :#line:7
    PY3 =True #line:8
    unicode =str #line:9
    unichr =chr #line:10
    long =int #line:11
    import urllib .parse as urllib #line:13
else :#line:14
    import urllib #line:15
import string #line:17
STANDARD_ALPHABET ='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='#line:19
CUSTOM_ALPHABET ='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/='#line:20
ENCODE_TRANS =''if PY3 else string .maketrans (STANDARD_ALPHABET ,CUSTOM_ALPHABET )#line:21
DECODE_TRANS =''if PY3 else string .maketrans (CUSTOM_ALPHABET ,STANDARD_ALPHABET )#line:22
def decode2 (O0OOO000O0OO0OOO0 ):#line:24
  O00000O00O00O000O =O0OOO000O0OO0OOO0 .translate (str .maketrans (STANDARD_ALPHABET ,CUSTOM_ALPHABET ))if PY3 else O0OOO000O0OO0OOO0 .translate (DECODE_TRANS )#line:26
  return base64 .b64decode (O00000O00O00O000O )#line:27
def getkey (OO0OOO0O000OOO00O ):#line:30
    class OO0000OOO0O0O000O (object ):#line:31
        def __init__ (OOOOO0O0OOOO0000O ,OO0OOO0O00OO0O0OO ):#line:33
            OOOOO0O0OOOO0000O .data =OO0OOO0O00OO0O0OO #line:34
            OOOOO0O0OOOO0000O .funcion =''#line:35
            OOOOO0O0OOOO0000O .lista =[]#line:36
            OOOOO0O0OOOO0000O .l1l1ll ,OOOOO0O0OOOO0000O .msg =OOOOO0O0OOOO0000O .l11ll1 ()#line:37
            if OOOOO0O0OOOO0000O .l1l1ll :#line:38
                OO00OO00OOOOO0O0O =re .compile ("""(%s\\(['"]([^'"]*)['"],\\s*['"]([^'"]*)['"]\\))"""%OOOOO0O0OOOO0000O .funcion ).findall (OOOOO0O0OOOO0000O .data )#line:40
                for OOO000O000OOO00OO ,O00OOO0O00OO0000O in enumerate (OO00OO00OOOOO0O0O ):#line:41
                    O0OOO0O0O00OOO0OO =OOOOO0O0OOOO0000O .unhex (O00OOO0O00OO0000O [2 ])if O00OOO0O00OO0000O [2 ][:2 ]=='\\x'else O00OOO0O00OO0000O [2 ]#line:42
                    O0000O000O0O0O00O =OOOOO0O0OOOO0000O .l1ll11 (int (O00OOO0O00OO0000O [1 ],16 ),O0OOO0O0O00OOO0OO )#line:43
                    if "'"not in O0000O000O0O0O00O :#line:44
                        OOOOO0O0OOOO0000O .data =OOOOO0O0OOOO0000O .data .replace (O00OOO0O00OO0000O [0 ],"'"+O0000O000O0O0O00O +"'")#line:45
                    elif '"'not in O0000O000O0O0O00O :#line:46
                        OOOOO0O0OOOO0000O .data =OOOOO0O0OOOO0000O .data .replace (O00OOO0O00OO0000O [0 ],'"'+O0000O000O0O0O00O +'"')#line:47
                    else :#line:48
                        return #line:49
                OO00OO00OOOOO0O0O =re .compile ("""(%s\\(\\\\['"](.*?)\\\\['"],\\s*\\\\['"](.*?)\\\\['"]\\))"""%OOOOO0O0OOOO0000O .funcion ).findall (OOOOO0O0OOOO0000O .data )#line:50
                for OOO000O000OOO00OO ,O00OOO0O00OO0000O in enumerate (OO00OO00OOOOO0O0O ):#line:52
                    O0OOO0O0O00OOO0OO =OOOOO0O0OOOO0000O .unhex (O00OOO0O00OO0000O [2 ])if O00OOO0O00OO0000O [2 ][:2 ]=='\\x'else O00OOO0O00OO0000O [2 ]#line:53
                    O0000O000O0O0O00O =OOOOO0O0OOOO0000O .l1ll11 (int (O00OOO0O00OO0000O [1 ],16 ),O0OOO0O0O00OOO0OO )#line:54
                    if "'"not in O0000O000O0O0O00O :#line:55
                        OOOOO0O0OOOO0000O .data =OOOOO0O0OOOO0000O .data .replace (O00OOO0O00OO0000O [0 ],"\\'"+O0000O000O0O0O00O +"\\'")#line:56
                    elif '"'not in O0000O000O0O0O00O :#line:57
                        OOOOO0O0OOOO0000O .data =OOOOO0O0OOOO0000O .data .replace (O00OOO0O00OO0000O [0 ],'\\"'+O0000O000O0O0O00O +'\\"')#line:58
                    else :#line:59
                        return #line:60
                OO00OO00OOOOO0O0O =re .compile ("""(%s\\(['"]([^'"]*)['"]\\))"""%OOOOO0O0OOOO0000O .funcion ).findall (OOOOO0O0OOOO0000O .data )#line:63
                for OOO000O000OOO00OO ,O00OOO0O00OO0000O in enumerate (OO00OO00OOOOO0O0O ):#line:65
                    O0000O000O0O0O00O =OOOOO0O0OOOO0000O .l1ll11 (int (OOOOO0O0OOOO0000O .unhex (O00OOO0O00OO0000O [1 ]),16 ),'')#line:67
                    if "'"not in O0000O000O0O0O00O :#line:68
                        OOOOO0O0OOOO0000O .data =OOOOO0O0OOOO0000O .data .replace (O00OOO0O00OO0000O [0 ],"'"+O0000O000O0O0O00O +"'")#line:69
                    elif '"'not in O0000O000O0O0O00O :#line:70
                        OOOOO0O0OOOO0000O .data =OOOOO0O0OOOO0000O .data .replace (O00OOO0O00OO0000O [0 ],'"'+O0000O000O0O0O00O +'"')#line:71
                    else :#line:72
                        return #line:73
                OO00OO00OOOOO0O0O =re .compile ("""(%s\\(\\\\['"](.*?)\\\\['"]\\))"""%OOOOO0O0OOOO0000O .funcion ).findall (OOOOO0O0OOOO0000O .data )#line:74
                for OOO000O000OOO00OO ,O00OOO0O00OO0000O in enumerate (OO00OO00OOOOO0O0O ):#line:76
                    O0000O000O0O0O00O =OOOOO0O0OOOO0000O .l1ll11 (int (O00OOO0O00OO0000O [1 ],16 ),'')#line:77
                    if "'"not in O0000O000O0O0O00O :#line:78
                        OOOOO0O0OOOO0000O .data =OOOOO0O0OOOO0000O .data .replace (O00OOO0O00OO0000O [0 ],"\\'"+O0000O000O0O0O00O +"\\'")#line:79
                    elif '"'not in O0000O000O0O0O00O :#line:80
                        OOOOO0O0OOOO0000O .data =OOOOO0O0OOOO0000O .data .replace (O00OOO0O00OO0000O [0 ],'\\"'+O0000O000O0O0O00O +'\\"')#line:81
                    else :#line:82
                        return #line:83
        def l11ll1 (O0OO00OOOOO0000OO ):#line:85
            OOO0000OOO0000OO0 =re .search ('var (\\w*)\\s*=\\s*\\[(.*?)\\];',O0OO00OOOOO0000OO .data )#line:86
            if not OOO0000OOO0000OO0 :#line:87
                return (False ,'')#line:88
            OO00OO0OOOOOOO00O =OOO0000OOO0000OO0 .group (1 )#line:89
            O0OO00OOOOO0000OO .lista =OOO0000OOO0000OO0 .group (2 ).split (',')#line:90
            for OO0O0OO00OO000OOO ,OOO0O0O00OOO0O000 in enumerate (O0OO00OOOOO0000OO .lista ):#line:91
                O0OO00OOOOO0000OO .lista [OO0O0OO00OO000OOO ]=OOO0O0O00OOO0O000 .strip ()[1 :-1 ]#line:92
            if O0OO00OOOOO0000OO .lista [0 ][:2 ]=='\\x':#line:94
                for OO0O0OO00OO000OOO ,OOO0O0O00OOO0O000 in enumerate (O0OO00OOOOO0000OO .lista ):#line:95
                    O0OO00OOOOO0000OO .lista [OO0O0OO00OO000OOO ]=O0OO00OOOOO0000OO .unhex (OOO0O0O00OOO0O000 )#line:96
            O0OO00OOOOO0000OO .data =O0OO00OOOOO0000OO .data .replace (OOO0000OOO0000OO0 .group (0 ),'')#line:98
            OOO0000OOO0000OO0 =re .search ('\\(function\\(.*?}\\(%s,\\s*([^\\)]*)\\)\\);'%OO00OO0OOOOOOO00O ,O0OO00OOOOO0000OO .data ,flags =re .DOTALL )#line:99
            if not OOO0000OOO0000OO0 :#line:100
                return (False ,'')#line:101
            OO00OOOO000OO0OOO =OOO0000OOO0000OO0 .group (1 )#line:102
            O0OOOOO0OOOOOO000 =eval (OO00OOOO000OO0OOO )#line:107
            O0OO00OOOOO0000OO .data =O0OO00OOOOO0000OO .data .replace (OOO0000OOO0000OO0 .group (0 ),'')#line:109
            for OO00O0O0O0O0O0000 in range (O0OOOOO0OOOOOO000 ):#line:110
                O0OO00OOOOO0000OO .lista .append (O0OO00OOOOO0000OO .lista .pop (0 ))#line:111
            O0O0000O0O0OO0000 ="""var (\w*)\s*=\s*function\s*\(\s*[0-9a-fA-F]+,\s*[0-9a-fA-F]+\s*\)\s*{\s*[0-9a-fA-F]+"""#line:114
            O00000OOO00OOOO00 ="""var (\w*)\s*=\s*function\s*\(\s*_0[xX][0-9a-fA-F]+\s*,\s*_0[xX][0-9a-fA-F]+"""#line:115
            OOO0000OOO0000OO0 =re .search (O0O0000O0O0OO0000 ,O0OO00OOOOO0000OO .data )#line:116
            OO00O00OO00OOOOO0 =re .search (O00000OOO00OOOO00 ,O0OO00OOOOO0000OO .data )#line:117
            if not OOO0000OOO0000OO0 and not OO00O00OO00OOOOO0 :#line:120
              return (False ,'')#line:121
            else :#line:122
              OOO0000OOO0000OO0 =OOO0000OOO0000OO0 if OOO0000OOO0000OO0 else OO00O00OO00OOOOO0 #line:123
            O0OO00OOOOO0000OO .funcion =OOO0000OOO0000OO0 .group (1 ).strip ()#line:130
            O0OO00OOOOO0000OO .data =O0OO00OOOOO0000OO .data .replace (OOO0000OOO0000OO0 .group (0 ),'')#line:131
            return (True ,'')#line:133
        def l1ll11 (OOOOOO0O0O0000O00 ,OOOO0OOOOOO00O00O ,O000O000OO00000O0 =''):#line:135
            OO00000O00O00OO00 =str (OOOOOO0O0O0000O00 .lista [OOOO0OOOOOO00O00O ])#line:136
            OO00000O00O00OO00 =decode2 (OO00000O00O00OO00 )#line:137
            if PY3 :#line:138
               OO00000O00O00OO00 =('').join (chr (OO00O000O0O00O00O )for OO00O000O0O00O00O in bytes (OO00000O00O00OO00 ))#line:139
            OOOOO0OOO0000OO0O =''#line:140
            for OOOO000O0OOO0OOO0 in range (len (OO00000O00O00OO00 )):#line:141
                OOOOO0OOO0000OO0O +='%'+('00'+hex (ord (OO00000O00O00OO00 [OOOO000O0OOO0OOO0 ]))[2 :])[-2 :]#line:142
            if PY3 :#line:144
                OO00000O00O00OO00 =urllib .unquote (OOOOO0OOO0000OO0O )#line:145
            else :#line:146
                OO00000O00O00OO00 =unicode (urllib .unquote (OOOOO0OOO0000OO0O ),'utf8')#line:147
            if O000O000OO00000O0 =='':#line:148
                return OO00000O00O00OO00 #line:149
            else :#line:150
                O0OO0O00O00000000 =list (range (256 ))#line:151
                OO000OO0OO0OO00OO =0 #line:152
                OO0OOOO0OOOO0O00O =''#line:153
                for OOOO000O0OOO0OOO0 in range (256 ):#line:154
                    OO000OO0OO0OO00OO =(OO000OO0OO0OO00OO +O0OO0O00O00000000 [OOOO000O0OOO0OOO0 ]+ord (O000O000OO00000O0 [(OOOO000O0OOO0OOO0 %len (O000O000OO00000O0 ))]))%256 #line:155
                    OOOOOOO0OO00O0OOO =O0OO0O00O00000000 [OOOO000O0OOO0OOO0 ]#line:156
                    O0OO0O00O00000000 [OOOO000O0OOO0OOO0 ]=O0OO0O00O00000000 [OO000OO0OO0OO00OO ]#line:157
                    O0OO0O00O00000000 [OO000OO0OO0OO00OO ]=OOOOOOO0OO00O0OOO #line:158
                O0OOO00O0O0OO0OO0 =0 #line:160
                OO000OO0OO0OO00OO =0 #line:161
                for OOOO000O0OOO0OOO0 in range (len (OO00000O00O00OO00 )):#line:162
                    O0OOO00O0O0OO0OO0 =(O0OOO00O0O0OO0OO0 +1 )%256 #line:163
                    OO000OO0OO0OO00OO =(OO000OO0OO0OO00OO +O0OO0O00O00000000 [O0OOO00O0O0OO0OO0 ])%256 #line:164
                    OOOOOOO0OO00O0OOO =O0OO0O00O00000000 [O0OOO00O0O0OO0OO0 ]#line:165
                    O0OO0O00O00000000 [O0OOO00O0O0OO0OO0 ]=O0OO0O00O00000000 [OO000OO0OO0OO00OO ]#line:166
                    O0OO0O00O00000000 [OO000OO0OO0OO00OO ]=OOOOOOO0OO00O0OOO #line:167
                    OO0OOOO0OOOO0O00O +=unichr (ord (OO00000O00O00OO00 [OOOO000O0OOO0OOO0 ])^O0OO0O00O00000000 [((O0OO0O00O00000000 [O0OOO00O0O0OO0OO0 ]+O0OO0O00O00000000 [OO000OO0OO0OO00OO ])%256 )])#line:168
                if PY3 :#line:170
                   return OO0OOOO0OOOO0O00O #line:171
                return OO0OOOO0OOOO0O00O .encode ('utf8')#line:172
        def unhex (O00000OO00O000OO0 ,OO0OO000OOOO0OOO0 ):#line:174
            if PY3 :#line:175
                O00OO0000OO00O000 =re .sub ('\\\\x[a-f0-9][a-f0-9]',lambda O0O00OO0OOOOO00O0 :bytes .fromhex (O0O00OO0OOOOO00O0 .group ()[2 :]).decode ('utf-8'),OO0OO000OOOO0OOO0 )#line:176
            else :#line:180
                O00OO0000OO00O000 =re .sub ('\\\\x[a-f0-9][a-f0-9]',lambda O0O00O00OOOOO00OO :O0O00O00OOOOO00OO .group ()[2 :].decode ('hex'),OO0OO000OOOO0OOO0 )#line:181
            return O00OO0000OO00O000 #line:182
    O0OOOO0OOO0O000O0 =OO0000OOO0O0O000O (OO0OOO0O000OOO00O )#line:183
    O0OO00OOOO0O0OOO0 =OO0000OOO0O0O000O (O0OOOO0OOO0O000O0 .data )#line:184
    def O00OO00O00O00O000 (OO0O00OO000000OOO ):#line:185
        if PY3 :#line:186
            OO00O000OOO0000O0 =re .sub ('\\\\x[a-f0-9][a-f0-9]',lambda OO0OO000OO0OO0O0O :bytes .fromhex (OO0OO000OO0OO0O0O .group ()[2 :]).decode ('utf-8'),OO0O00OO000000OOO )#line:187
        else :#line:191
            OO00O000OOO0000O0 =re .sub ('\\\\x[a-f0-9][a-f0-9]',lambda O0O00OO00O000OO0O :O0O00OO00O000OO0O .group ()[2 :].decode ('hex'),OO0O00OO000000OOO )#line:192
        return OO00O000OOO0000O0 #line:193
    return O00OO00O00O00O000 (O0OO00OOOO0O0OOO0 .data )#line:198
