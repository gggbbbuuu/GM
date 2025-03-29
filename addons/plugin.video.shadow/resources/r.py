import re,os
import codecs
from os import listdir
from os.path import isfile, join
file = codecs.open('settings.xml', 'r', 'UTF-8') 
fans= file.read()

file.close()
types=['Movie','TV']
for i in types:
    regex='<!--%s Sources-->(.+?)<!--End %s Sources-->'%(i,i)
    m=re.compile(regex,re.DOTALL).findall(fans)[0]
    
    source_dir=os.path.join(os.getcwd(),'sources')
    onlyfiles = [f for f in listdir(source_dir) if (isfile(join(source_dir, f)) and f.endswith('.py') and '__init__' not in f)]
    f_txt=['\n']
    for item in onlyfiles:
        file=codecs.open(os.path.join(source_dir,item), 'r', 'UTF-8')
        #file = open(os.path.join(source_dir,item), 'r') 
        f_data= file.read()
        file.close()
        added_t=''
        if 'non_rd' in f_data:
            added_t=' [COLOR lightblue](Free)[/COLOR]'
        if 'easynews' in f_data or 'furk' in f_data:
            added_t=' [COLOR red](Paid)[/COLOR]'
        added_id=''
        if i=='TV':
            added_id='_tv'
        f_txt.append('		<setting id="%s" label="%s" type="bool"  default="true" />'%(item.replace('.py','')+added_id,item.replace('.py','')+added_t))
    f_txt.append('\n')
   
    fans=fans.replace(m,'\n'.join(f_txt))
   
file = codecs.open('settings.xml', 'w', 'UTF-8') 
             
file.write(fans)
file.close()