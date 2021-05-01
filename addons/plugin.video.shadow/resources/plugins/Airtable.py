"""
Usage Examples:


    Returns the Tv Channels-

    <dir>
    <title>Tv Channels</title>
    <Airtable>tv_channels</Airtable>
    </dir>

    Tv Channels2 are links that dont require plugins

    <dir>
    <title>Tv Channels2</title>
    <Airtable>channels2</Airtable>
    </dir>

    Returns the Sports Channels-

    <dir>
    <title>Sports Channels</title>
    <Airtable>sports_channels</Airtable>
    </dir>


    Returns the 24-7 Channels
    <dir>
    <title>24-7 Channels</title>
    <Airtable>247</Airtable>
    </dir>

    --------------------------------------------------------------

"""
from resources.modules import public
import logging,xbmcplugin,sys
addDir3=public.addDir3
addLink=public.addLink
from  resources.modules.client import get_html
def run(url,lang,icon,fanart,plot,name):
    return addDir3(name,'Airtable',193,icon,fanart,plot,id=url)
        
def next_level(url,icon,fanart,plot,name,id):
    import posixpath
    if id=='247':
        table_name = 'twenty_four_seven'
        table_key='appMiehwc18Akz8Zv'
    elif id=='Tv_channels':
        table_key = 'appw1K6yy7YtatXbm'
        table_name = 'TV_channels'
    elif id=='Sports_channels':
        table_key = 'appFVmVwiMw0AS1cJ'
        table_name = 'Sports_channels'
    ur=posixpath.join('https://api.airtable.com/','v0', table_key,table_name)
    
    headers={'Authorization': 'Bearer {0}'.format('keyikW1exArRfNAWj')}
    x=get_html(ur,headers=headers,verify=False).json()
    
    
    all_d=[]
    for field in x['records']:
        links=[]
        res = field['fields']
        title=res['channel']
        channel = res['channel']
        thumbnail = res['thumbnail']
        fanart = res['fanart']
        category = res['category']
        if len(thumbnail)<2:
            thumbnail=icon
        if len(res['link'])>2:
            links .append( res['link'])
        if len(res['link2'])>2:
            links .append( res['link2'])
        if len(res['link3'])>2:
            links .append( res['link3'])
        if len(links)==0:
            continue
        if len(links)>1:
            f_link='$$$$'.join(links)
        else:
            f_link=links[0]
        
        aa=addLink(title,f_link,6,False,thumbnail,fanart,category,original_title=title,place_control=True)
        all_d.append(aa)
    xbmcplugin .addDirectoryItems(int(sys.argv[1]),all_d,len(all_d))