import time,xbmcplugin,os,json,sys

from resources.modules.public import *
global CLIENT_ID,CLIENT_SECRET

#trakt api keys
CLIENT_ID = "8ed545c0b7f92cc26d1ecd6326995c6cf0053bd7596a98e962a472bee63274e6"
CLIENT_SECRET = "1ec4f37e5743e3086abace0c83444c25d9b655d1d77b793806b2c8205a510426"

lang=xbmc.getLanguage(0)
addonPath = xbmc_tranlate_path(Addon.getAddonInfo("path"))
if Addon.getSetting("theme")=='0':
    art_folder='artwork'
    
elif Addon.getSetting("theme")=='1':
    art_folder='artwork_keshav'
elif Addon.getSetting("theme")=='2':
    art_folder='artwork_shinobi'
elif Addon.getSetting("theme")=='3':
    art_folder='artwork_sonic'
elif Addon.getSetting("theme")=='4':
    art_folder='artwork_bob'
    
BASE_LOGO=os.path.join(addonPath, 'resources', art_folder+'/')
file = open(os.path.join(BASE_LOGO, 'fanart.json'), 'r') 
fans= file.read()
file.close()
fanarts=json.loads(fans)
all_fanarts={}
for items in fanarts:
    if 'http' in fanarts[items]:
        all_fanarts[items]=fanarts[items]
    else:
        all_fanarts[items]=(os.path.join(BASE_LOGO, fanarts[items]))
    


def main_menu():


    
    all_d=[]
   
    if Addon.getSetting('movie_world')=='true':
        aa=addDir3(Addon.getLocalizedString(32024),'www',2,BASE_LOGO+'movies.png',all_fanarts['32024'],'Movies')
        all_d.append(aa)
    if Addon.getSetting('tv_world')=='true':
        aa=addDir3(Addon.getLocalizedString(32025),'www',3,BASE_LOGO+'tv.png',all_fanarts['32025'],'TV')
        all_d.append(aa)
    #aa=addDir3('One Click free','www',198,'https://i1.wp.com/reviewvpn.com/wp-content/uploads/2020/07/How-to-Install-T2K-One-Click-Movie-Addon-e1595234117323.png?fit=305%2C321&ssl=1','https://i1.wp.com/paulsohn.org/wp-content/uploads/2012/05/movie-click.jpg','Movies')
    #all_d.append(aa)
    if Addon.getSetting('trakt_world')=='true':
        aa=addDir3(Addon.getLocalizedString(32026),'www',21,BASE_LOGO+'trakt.png',all_fanarts['32026'],'No account needed)')
        all_d.append(aa)
    if Addon.getSetting('trakt')=='true':
        aa=addDir3(Addon.getLocalizedString(32027),'www',114,BASE_LOGO+'trakt.png',all_fanarts['32027'],'TV')
        all_d.append(aa)
    if Addon.getSetting('search')=='true':
        aa=addDir3(Addon.getLocalizedString(32020),'www',5,BASE_LOGO+'search.png',all_fanarts['32020'],'Search')
        all_d.append(aa)
    if Addon.getSetting('search_history')=='true':
        aa=addDir3(Addon.getLocalizedString(32021),'both',143,BASE_LOGO+'search.png',all_fanarts['32021'],'TMDB')
        all_d.append(aa)
    if Addon.getSetting('last_link_played')=='true':
        aa=addDir3(Addon.getLocalizedString(32022),'www',144,BASE_LOGO+'last.png',all_fanarts['32022'],'Last Played') 
        all_d.append(aa)
    if Addon.getSetting('whats_new')=='true':
        aa=addNolink(Addon.getLocalizedString(32028) , 'www',149,False,fanart=all_fanarts['32028'], iconimage=BASE_LOGO+'news.png',plot='',dont_place=True)
        all_d.append(aa)
    if Addon.getSetting('settings')=='true':
        aa=addNolink( Addon.getLocalizedString(32029), 'www',151,False,fanart=all_fanarts['32029'], iconimage=BASE_LOGO+'setting.png',plot='',dont_place=True)
        all_d.append(aa)
    if Addon.getSetting('resume_watching')=='true':		
        aa=addDir3(Addon.getLocalizedString(32030),'both',158,BASE_LOGO+'resume.png',all_fanarts['32030'],'TMDB')
        all_d.append(aa)
    if Addon.getSetting('debrid_use_rd')=='true':
        if Addon.getSetting('my_rd_history')=='true':
            aa=addDir3(Addon.getLocalizedString(32031),'1',168,BASE_LOGO+'rd_history.png',all_fanarts['32031'],'TMDB')
            all_d.append(aa)
        if Addon.getSetting('rd_Torrents')=='true':
            aa=addDir3(Addon.getLocalizedString(32032),'1',169,BASE_LOGO+'rd_Torrents.png',all_fanarts['32032'],'TMDB')
            all_d.append(aa)
    if Addon.getSetting('actor')=='true':
        aa=addDir3(Addon.getLocalizedString(32033),'www',72,BASE_LOGO+'actor.png',all_fanarts['32033'],'Actor')
        all_d.append(aa)
    if Addon.getSetting('scraper_check')=='true':
        aa=addDir3( Addon.getLocalizedString(32034), 'www',172,BASE_LOGO+'basic.png',all_fanarts['32034'],'Test')
        
        all_d.append(aa)
    
    #Ghost
    #place your Jen playlist here:
    #dulpicate this line with your address
    #aa=addDir3('Name', 'Your Jen Address',189,'Iconimage','fanart','Description',search_db='Your Search db Address')
    #all_d.append(aa)
    #'https://narcacist.com/Jen4k/4ksection.json'
    mypass=""
    key='zWrite'
    mypass=crypt(mypass,key)

    aa=addDir3('Odin', 'https://mylostsoulspace.co.uk/Addon-1/Addon/text/rd/4ksection.xml',189,'https://narcacist.com/images/Odin/icon.png','https://narcacist.com/images/Odin/fanart.jpg','Odin',mypass=mypass,search_db='http://tazaddon.com/TazClicks/search.db')
    all_d.append(aa)
    
    aa=addDir3( 'Search All', 'www',201,BASE_LOGO+'search.png',all_fanarts['32034'],'Search All')
        
    all_d.append(aa)
        
    #place your MicroJen playlist here:
    #dulpicate this line with your address
    #aa=addDir3('Name', 'Your Jen Address',189,'Iconimage','fanart','Description',search_db='Your Search db Address')
    #all_d.append(aa)
    #aa=addDir3('MicroJen', "https://bitbucket.org/Mad-Eric/textfiles/raw/master/NewMav/MavHome.json",189,'https://www.nylas.com/wp-content/uploads/JSON_Blog_Hero.png','https://i.ytimg.com/vi/9N6a-VLBa2I/maxresdefault.jpg','MicroJen')
    #all_d.append(aa)
    
    if Addon.getSetting('debug')=='true':
        aa=addDir3( 'Unit tests', 'www',181,'https://lh3.googleusercontent.com/proxy/Ia9aOfcgtzofMb0urCAs8NV-4RRhcIVST-Gqx9GI9RLsx7IJe_5jBqjfdsJcOO3QIV3TT-uiF2nKmyYCX0vj5UPR4iW1iHXgZylE8N8wyNgRLw','https://i.ytimg.com/vi/3wLqsRLvV-c/maxresdefault.jpg','Test')
        
        all_d.append(aa)
    if Addon.getSetting('doodstream')=='true':
        aa=addDir3( "My Doodsteam Files", '1',202,BASE_LOGO+'basic.png',all_fanarts['32034'],'Test',id="")
        
        all_d.append(aa)
    found=False
    for i in range(0,10):
        if Addon.getSetting('imdb_user_'+str(i))!='':
            found=True
            break
    if found:
        aa=addDir3(Addon.getLocalizedString(32309),'www',183,BASE_LOGO+'basic.png',all_fanarts['32309'],'Imdb')
        all_d.append(aa)
    
    
    if Addon.getSetting("stop_where")=='0':
            xbmcplugin .addDirectoryItems(int(sys.argv[1]),all_d,len(all_d))
    
    
def movie_world():
    all_d=[]
    try:
        from sqlite3 import dbapi2 as database
    except:
        from pysqlite2 import dbapi2 as database
    cacheFile=os.path.join(user_dataDir,'database.db')
    dbcon = database.connect(cacheFile)
    dbcur = dbcon.cursor()
    dbcur.execute("CREATE TABLE IF NOT EXISTS %s ( ""name TEXT, ""url TEXT, ""tv_movie TEXT);" % 'add_cat')
    
   
    dbcon.commit()
    dbcur.execute("SELECT * FROM add_cat")
    match = dbcur.fetchall()
    dbcur.close()
    dbcon.close()
    
    all_s_strings=[]
    for name,url,tv_movie in match:
        
        if (tv_movie=='movie'):
           aa=addDir3('[COLOR lightblue][B]'+name+'[/B][/COLOR]',url,14,BASE_LOGO+'int.png',all_fanarts['32295'],'Tmdb_custom')
           all_d.append(aa)
    
    aa=addDir3(Addon.getLocalizedString(32295),f'https://api.themoviedb.org/3/movie/now_playing?api_key={tmdb_key}&language=%s&page=1'%lang,14,BASE_LOGO+'int.png',all_fanarts['32295'],'Tmdb')
    all_d.append(aa)
    'Popular Movies'
    aa=addDir3(Addon.getLocalizedString(32036),f'https://api.themoviedb.org/3/movie/popular?api_key={tmdb_key}&language=%s&page=1'%lang,14,BASE_LOGO+'popular.png',all_fanarts['32036'],'Tmdb')
    all_d.append(aa)
    'Released Movies'
    aa=addDir3('Released Movies',f'https://api.themoviedb.org/3/movie/popular?api_key={tmdb_key}&language=%s&with_release_type=4&page=1'%lang,14,BASE_LOGO+'popular.png',all_fanarts['32036'],'Tmdb')
    all_d.append(aa)
    
    aa=addDir3(Addon.getLocalizedString(32037),f'https://api.themoviedb.org/3/search/movie?api_key={tmdb_key}&query=3d&language=%s&append_to_response=origin_country&page=1'%lang,14,BASE_LOGO+'3d.png',all_fanarts['32037'],'Tmdb')
    all_d.append(aa)
    
    #Genre
    aa=addDir3(Addon.getLocalizedString(32038),f'https://api.themoviedb.org/3/genre/movie/list?api_key={tmdb_key}&language=%s&page=1'%lang,18,BASE_LOGO+'genre.png',all_fanarts['32038'],'Tmdb')
    all_d.append(aa)
    #Years
    aa=addDir3(Addon.getLocalizedString(32039),'movie_years&page=1',14,BASE_LOGO+'years.png',all_fanarts['32039'],'Tmdb')
    all_d.append(aa)
    aa=addDir3(Addon.getLocalizedString(32040),'movie_years&page=1',112,BASE_LOGO+'studio.png',all_fanarts['32040'],'Tmdb')
    all_d.append(aa)
    aa=addDir3(Addon.getLocalizedString(32041),'advance_movie',14,BASE_LOGO+'content_s.png',all_fanarts['32041'],'Advance Content selection')
    all_d.append(aa)
    #Search movie
    aa=addDir3(Addon.getLocalizedString(32042),f'https://api.themoviedb.org/3/search/movie?api_key={tmdb_key}&query=%s&language={lang}&append_to_response=origin_country&page=1'.format(lang),14,BASE_LOGO+'search_m.png',all_fanarts['32042'],'Tmdb')
    all_d.append(aa)
    aa=addDir3(Addon.getLocalizedString(32043),'movie',143,BASE_LOGO+'search.png',all_fanarts['32043'],'TMDB')
    all_d.append(aa)
    try:
        from sqlite3 import dbapi2 as database
    except:
        from pysqlite2 import dbapi2 as database
    cacheFile=os.path.join(user_dataDir,'database.db')
    dbcon = database.connect(cacheFile)
    dbcur = dbcon.cursor()
    
    table_name='lastlinkmovie'
    
    dbcur.execute("CREATE TABLE IF NOT EXISTS %s ( ""o_name TEXT,""name TEXT, ""url TEXT, ""iconimage TEXT, ""fanart TEXT,""description TEXT,""data TEXT,""season TEXT,""episode TEXT,""original_title TEXT,""saved_name TEXT,""heb_name TEXT,""show_original_year TEXT,""eng_name TEXT,""isr TEXT,""prev_name TEXT,""id TEXT);"%table_name)
    
    dbcur.execute("SELECT * FROM lastlinkmovie WHERE o_name='f_name'")

    match = dbcur.fetchone()
    dbcon.commit()
    
    dbcur.close()
    dbcon.close()
    
    if match!=None:
       f_name,name,url,iconimage,fanart,description,data,season,episode,original_title,saved_name,heb_name,show_original_year,eng_name,isr,prev_name,id=match
       try:
           if url!=' ':
             if 'http' not  in url:
           
               url=base64.b64decode(url)
              
             aa=addLink('[I]%s[/I]'%Addon.getLocalizedString(32022), url,6,False,iconimage,fanart,description,data=show_original_year,prev_name=name,original_title=original_title,season=season,episode=episode,tmdb=id,year=show_original_year,place_control=True)
             all_d.append(aa)
       except  Exception as e:
         log.warning(e)
         pass
    aa=addDir3(Addon.getLocalizedString(32044),'movie',145,BASE_LOGO+'history.png',all_fanarts['32044'],'History')
    
    all_d.append(aa)
    aa=addDir3(Addon.getLocalizedString(32045),'0',174,BASE_LOGO+'classic.png',all_fanarts['32045'],'classic')
    
    all_d.append(aa)
    
    aa=addDir3(Addon.getLocalizedString(32046),'0',176,BASE_LOGO+'westren.png',all_fanarts['32046'],'classic')
    
    all_d.append(aa)
    
    aa=addDir3(Addon.getLocalizedString(32047),'0',178,BASE_LOGO+'3d_free.png',all_fanarts['32047'],'3D')
    
    all_d.append(aa)
    
    aa=addDir3(Addon.getLocalizedString(32313),'0',187,BASE_LOGO+'keywords.png',all_fanarts['32313'],'keywords')
    
    all_d.append(aa)
    #place your Jen playlist here:
    #dulpicate this line with your address
    #aa=addDir3('Name', 'Your Jen Address',189,'Iconimage','fanart','Description',search_db='Your Search db Address')
    #all_d.append(aa)
    
    xbmcplugin .addDirectoryItems(int(sys.argv[1]),all_d,len(all_d))

def movie_prodiction():
    all_d=[]
    if Addon.getSetting("order_networks")=='0':
        order_by='popularity.desc'
    elif Addon.getSetting("order_networks")=='2':
        order_by='vote_average.desc'
    elif Addon.getSetting("order_networks")=='1':
        order_by='first_air_date.desc'
    
    
    aa=addDir3('[COLOR red]Marvel[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=7505&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://yt3.ggpht.com/a-/AN66SAwQlZAow0EBMi2-tFht-HvmozkqAXlkejVc4A=s900-mo-c-c0xffffffff-rj-k-no','https://images-na.ssl-images-amazon.com/images/I/91YWN2-mI6L._SL1500_.jpg','Marvel')
    all_d.append(aa)
    aa=addDir3('[COLOR lightblue]DC Studios[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=9993&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://pmcvariety.files.wordpress.com/2013/09/dc-comics-logo.jpg?w=1000&h=563&crop=1','http://www.goldenspiralmedia.com/wp-content/uploads/2016/03/DC_Comics.jpg','DC Studios')
    all_d.append(aa)
    aa=addDir3('[COLOR lightgreen]Lucasfilm[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=1&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://fontmeme.com/images/lucasfilm-logo.png','https://i.ytimg.com/vi/wdYaG3o3bgE/maxresdefault.jpg','Lucasfilm')
    all_d.append(aa)
    aa=addDir3('[COLOR yellow]Warner Bros.[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=174&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'http://looking.la/wp-content/uploads/2017/10/warner-bros.png','https://cdn.arstechnica.net/wp-content/uploads/2016/09/warner.jpg','SyFy')
    all_d.append(aa)
    aa=addDir3('[COLOR blue]Walt Disney Pictures[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=2&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://i.ytimg.com/vi/9wDrIrdMh6o/hqdefault.jpg','https://vignette.wikia.nocookie.net/logopedia/images/7/78/Walt_Disney_Pictures_2008_logo.jpg/revision/latest?cb=20160720144950','Walt Disney Pictures')
    all_d.append(aa)
    aa=addDir3('[COLOR skyblue]Pixar[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=3&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://elestoque.org/wp-content/uploads/2017/12/Pixar-lamp.png','https://wallpapercave.com/wp/GysuwJ2.jpg','Pixar')
    all_d.append(aa)
    aa=addDir3('[COLOR deepskyblue]Paramount[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=4&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://upload.wikimedia.org/wikipedia/en/thumb/4/4d/Paramount_Pictures_2010.svg/1200px-Paramount_Pictures_2010.svg.png','https://vignette.wikia.nocookie.net/logopedia/images/a/a1/Paramount_Pictures_logo_with_new_Viacom_byline.jpg/revision/latest?cb=20120311200405&format=original','Paramount')
    all_d.append(aa)
    aa=addDir3('[COLOR burlywood]Columbia Pictures[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=5&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://static.tvtropes.org/pmwiki/pub/images/lady_columbia.jpg','https://vignette.wikia.nocookie.net/marveldatabase/images/1/1c/Columbia_Pictures_%28logo%29.jpg/revision/latest/scale-to-width-down/1000?cb=20141130063022','Columbia Pictures')
    all_d.append(aa)
    aa=addDir3('[COLOR powderblue]DreamWorks[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=7&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://www.dreamworksanimation.com/share.jpg','https://www.verdict.co.uk/wp-content/uploads/2017/11/DA-hero-final-final.jpg','DreamWorks')
    all_d.append(aa)
    aa=addDir3('[COLOR lightsaltegray]Miramax[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=14&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://vignette.wikia.nocookie.net/disney/images/8/8b/1000px-Miramax_1987_Print_Logo.png/revision/latest?cb=20140902041428','https://i.ytimg.com/vi/4keXxB94PJ0/maxresdefault.jpg','Miramax')
    all_d.append(aa)
    aa=addDir3('[COLOR gold]20th Century Fox[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=25&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://pmcdeadline2.files.wordpress.com/2017/03/20th-century-fox-cinemacon1.jpg?w=446&h=299&crop=1','https://vignette.wikia.nocookie.net/simpsons/images/8/80/TCFTV_logo_%282013-%3F%29.jpg/revision/latest?cb=20140730182820','20th Century Fox')
    all_d.append(aa)
    aa=addDir3('[COLOR bisque]Sony Pictures[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=34&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://upload.wikimedia.org/wikipedia/commons/thumb/6/63/Sony_Pictures_Television_logo.svg/1200px-Sony_Pictures_Television_logo.svg.png','https://vignette.wikia.nocookie.net/logopedia/images/2/20/Sony_Pictures_Digital.png/revision/latest?cb=20140813002921','Sony Pictures')
    all_d.append(aa)
    aa=addDir3('[COLOR navy]Lions Gate Films[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=35&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'http://image.wikifoundry.com/image/1/QXHyOWmjvPRXhjC98B9Lpw53003/GW217H162','https://vignette.wikia.nocookie.net/fanon/images/f/fe/Lionsgate.jpg/revision/latest?cb=20141102103150','Lions Gate Films')
    all_d.append(aa)
    aa=addDir3('[COLOR beige]Orion Pictures[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=41&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://i.ytimg.com/vi/43OehM_rz8o/hqdefault.jpg','https://i.ytimg.com/vi/g58B0aSIB2Y/maxresdefault.jpg','Lions Gate Films')
    all_d.append(aa)
    aa=addDir3('[COLOR yellow]MGM[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=21&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://pbs.twimg.com/profile_images/958755066789294080/L9BklGz__400x400.jpg','https://assets.entrepreneur.com/content/3x2/2000/20150818171949-metro-goldwun-mayer-trade-mark.jpeg','MGM')
    all_d.append(aa)
    aa=addDir3('[COLOR gray]New Line Cinema[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=12&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://upload.wikimedia.org/wikipedia/en/thumb/0/04/New_Line_Cinema.svg/1200px-New_Line_Cinema.svg.png','https://vignette.wikia.nocookie.net/theideas/images/a/aa/New_Line_Cinema_logo.png/revision/latest?cb=20180210122847','New Line Cinema')
    all_d.append(aa)
    aa=addDir3('[COLOR darkblue]Gracie Films[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=18&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://i.ytimg.com/vi/q_slAJmZBeQ/hqdefault.jpg','https://i.ytimg.com/vi/yGofbuJTb4g/maxresdefault.jpg','Gracie Films')
    all_d.append(aa)
    aa=addDir3('[COLOR goldenrod]Imagine Entertainment[/COLOR]',f'https://api.themoviedb.org/3/discover/movie?api_key={tmdb_key}&with_companies=23&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://s3.amazonaws.com/fs.goanimate.com/files/thumbnails/movie/2813/1661813/9297975L.jpg','https://www.24spoilers.com/wp-content/uploads/2004/06/Imagine-Entertainment-logo.jpg','Imagine Entertainment')
    all_d.append(aa)
    xbmcplugin .addDirectoryItems(int(sys.argv[1]),all_d,len(all_d))
def main_trakt():
   all_d=[]
   aa=addDir3(Addon.getLocalizedString(32048),'movie?limit=40&page=1',116,BASE_LOGO+'lists.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Lists')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32049),'tv?limit=40&page=1',116,BASE_LOGO+'lists.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Lists')
   all_d.append(aa)
   import datetime
   current_date = adjusted_datetime()
   start = (current_date - datetime.timedelta(days=14)).strftime('%Y-%m-%d')
   finish = 14
        
   aa=addDir3(Addon.getLocalizedString(32050),'calendars/my/shows/%s/%s?limit=40&page=1'%(start,finish),117,BASE_LOGO+'lists.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Lists')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32051),'users/me/watched/shows?extended=full&limit=40&page=1',115,BASE_LOGO+'progress.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Progress')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32052),'sync/watchlist/episodes?extended=full&limit=40&page=1',115,BASE_LOGO+'ep_watch.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Episodes')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32053),'users/me/watchlist/episodes?extended=full&limit=40&page=1',117,BASE_LOGO+'series_w.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Series')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32054),'users/me/collection/shows?limit=40&page=1',117,BASE_LOGO+'tv_col.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','TV')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32055),'users/me/watchlist/shows?limit=40&page=1',117,BASE_LOGO+'show_w.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Shows')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32056),'recommendations/shows?limit=40&ignore_collected=true&page=1',166,BASE_LOGO+'trakt.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Movies')
   all_d.append(aa)
   
   aa=addDir3(Addon.getLocalizedString(32057),'users/me/watchlist/movies?limit=40&page=1',117,BASE_LOGO+'movie_wl.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Movies')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32058),'recommendations/movies?limit=40&ignore_collected=true&page=1',166,BASE_LOGO+'trakt.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Movies')
   all_d.append(aa)
   
   aa=addDir3(Addon.getLocalizedString(32059),'users/me/watched/movies?limit=40&page=1',117,BASE_LOGO+'movie_w.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Watched')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32060),'users/me/watched/shows?limit=40&page=1',117,BASE_LOGO+'series_wa.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Watched shows')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32061),'users/me/collection/movies?limit=40&page=1',117,BASE_LOGO+'movie_c.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','collection')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32062),'users/likes/lists?limit=40&page=1',118,BASE_LOGO+'liked_l.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Liked lists')
   all_d.append(aa)
   aa=addDir3(Addon.getLocalizedString(32063),'sync/playback/movies?limit=40&page=1',117,BASE_LOGO+'liked_l.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Liked lists')
   all_d.append(aa)
   
   aa=addDir3(Addon.getLocalizedString(32064),'sync/playback/episodes?limit=40&page=1',164,BASE_LOGO+'liked_l.png','https://seo-michael.co.uk/content/images/2016/08/trakt.jpg','Liked lists')
   all_d.append(aa)
   
   xbmcplugin .addDirectoryItems(int(sys.argv[1]),all_d,len(all_d))

def tv_show_menu():
    all_d=[]
    try:
        from sqlite3 import dbapi2 as database
    except:
        from pysqlite2 import dbapi2 as database
    cacheFile=os.path.join(user_dataDir,'database.db')
    dbcon = database.connect(cacheFile)
    dbcur = dbcon.cursor()
    dbcur.execute("CREATE TABLE IF NOT EXISTS %s ( ""name TEXT, ""url TEXT, ""tv_movie TEXT);" % 'add_cat')
    
   
    dbcon.commit()
    dbcur.execute("SELECT * FROM add_cat")
    match = dbcur.fetchall()
    dbcur.close()
    dbcon.close()
    
    all_s_strings=[]
    for name,url,tv_movie in match:
        
        if (tv_movie=='tv'):
           aa=addDir3('[COLOR lightblue][B]'+name+'[/B][/COLOR]',url,14,BASE_LOGO+'int.png',all_fanarts['32295'],'Tmdb_custom')
           all_d.append(aa)
    import datetime
    now = datetime.datetime.now()
    aa=addDir3(Addon.getLocalizedString(32023),'tv',145,BASE_LOGO+'tracker.png',all_fanarts['32023'],'History')
    #Popular
    aa=addDir3(Addon.getLocalizedString(32012),f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&language={lang}&sort_by=popularity.desc&include_null_first_air_dates=false&with_original_language=en&page=1',14,BASE_LOGO+'popular.png',all_fanarts['32013'],Addon.getLocalizedString(32012))
    all_d.append(aa)

    aa=addDir3(Addon.getLocalizedString(32013),f'https://api.themoviedb.org/3/tv/on_the_air?api_key={tmdb_key}&language=%s&page=1'%lang,14,BASE_LOGO+'on_air.png',all_fanarts['32013'],'TMDB')
    all_d.append(aa)
    
    
    aa=addDir3(Addon.getLocalizedString(32014),f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&language={lang}&sort_by=popularity.desc&first_air_date_year='+str(now.year)+f'&with_original_language=en&language={lang}&page=1',14,'special://home/addons/plugin.video.telemedia/tele/Tv_Show/popular_tv.png','special://home/addons/plugin.video.telemedia/tele/tv_fanart.png','New Tv shows')
    all_d.append(aa)
    #new episodes
    aa=addDir3(Addon.getLocalizedString(32015),'https://api.tvmaze.com/schedule',20,BASE_LOGO+'new_ep.png',all_fanarts['32015'],'New Episodes')
    all_d.append(aa)
    #Genre
    aa=addDir3(Addon.getLocalizedString(32016),f'https://api.themoviedb.org/3/genre/tv/list?api_key={tmdb_key}&language=%s&page=1'%lang,18,BASE_LOGO+'genre.png',all_fanarts['32016'],'TMDB')
    all_d.append(aa)
    #Years
    aa=addDir3(Addon.getLocalizedString(32017),'tv_years&page=1',14,BASE_LOGO+'years.png',all_fanarts['32017'],'TMDB')
    all_d.append(aa)
    aa=addDir3(Addon.getLocalizedString(32018),'tv_years&page=1',101,BASE_LOGO+'networks.png',all_fanarts['32018'],'TMDB')
    all_d.append(aa)
    aa=addDir3(Addon.getLocalizedString(32019),'advance_tv',14,BASE_LOGO+'content_s.png',all_fanarts['32019'],'Advance Content selection')
    
    all_d.append(aa)
    #Search tv
    aa=addDir3(Addon.getLocalizedString(32020),f'https://api.themoviedb.org/3/search/tv?api_key={tmdb_key}&query=%s&language={lang}&page=1'.format(lang),14,BASE_LOGO+'search.png',all_fanarts['32020'],'TMDB')
    all_d.append(aa)
    aa=addDir3(Addon.getLocalizedString(32021),'tv',143,BASE_LOGO+'search.png',all_fanarts['32021'],'TMDB')
    all_d.append(aa)
    
    try:
        from sqlite3 import dbapi2 as database
    except:
        from pysqlite2 import dbapi2 as database
    cacheFile=os.path.join(user_dataDir,'database.db')
    dbcon = database.connect(cacheFile)
    dbcur = dbcon.cursor()
    
    table_name='lastlinktv'
    
    dbcur.execute("CREATE TABLE IF NOT EXISTS %s ( ""o_name TEXT,""name TEXT, ""url TEXT, ""iconimage TEXT, ""fanart TEXT,""description TEXT,""data TEXT,""season TEXT,""episode TEXT,""original_title TEXT,""saved_name TEXT,""heb_name TEXT,""show_original_year TEXT,""eng_name TEXT,""isr TEXT,""prev_name TEXT,""id TEXT);"%table_name)
    
    dbcur.execute("SELECT * FROM lastlinktv WHERE o_name='f_name'")

    match = dbcur.fetchone()
    dbcon.commit()
    
    dbcur.close()
    dbcon.close()
    
    if match!=None:
       f_name,name,url,iconimage,fanart,description,data,season,episode,original_title,saved_name,heb_name,show_original_year,eng_name,isr,prev_name,id=match
       try:
           if url!=' ':
             if 'http' not  in url:
           
               url=base64.b64decode(url)
              
             aa=addLink('[I]%s[/I]'%Addon.getLocalizedString(32022), url,6,False,iconimage,fanart,description,data=show_original_year,original_title=original_title,season=season,episode=episode,tmdb=id,year=show_original_year,place_control=True)
             all_d.append(aa)
       except  Exception as e:
         log.warning(e)
         pass
         
    
    
    
    aa=addDir3(Addon.getLocalizedString(32023),'tv',145,BASE_LOGO+'tracker.png',all_fanarts['32023'],'History')
    all_d.append(aa)
    
    xbmcplugin .addDirectoryItems(int(sys.argv[1]),all_d,len(all_d))
def tv_neworks():
    all_d=[]
    if Addon.getSetting("order_networks")=='0':
        order_by='popularity.desc'
    elif Addon.getSetting("order_networks")=='2':
        order_by='vote_average.desc'
    elif Addon.getSetting("order_networks")=='1':
        order_by='first_air_date.desc'
    aa=addDir3('[COLOR lightblue]Disney+[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=2739&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://lumiere-a.akamaihd.net/v1/images/image_308e48ed.png','https://allears.net/wp-content/uploads/2018/11/wonderful-world-of-animation-disneys-hollywood-studios.jpg','Disney')
    all_d.append(aa)
    aa=addDir3('[COLOR blue]Apple TV+[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=2552&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://ksassets.timeincuk.net/wp/uploads/sites/55/2019/03/Apple-TV-screengrab-920x584.png','https://www.apple.com/newsroom/videos/apple-tv-plus-/posters/Apple-TV-app_571x321.jpg.large.jpg','Apple')
    all_d.append(aa)
    aa=addDir3('[COLOR red]NetFlix[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=213&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://art.pixilart.com/705ba833f935409.png','https://i.ytimg.com/vi/fJ8WffxB2Pg/maxresdefault.jpg','NetFlix')
    all_d.append(aa)
    aa=addDir3('[COLOR gray]HBO[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=49&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://filmschoolrejects.com/wp-content/uploads/2018/01/hbo-logo.jpg','https://www.hbo.com/content/dam/hbodata/brand/hbo-static-1920.jpg','HBO')
    all_d.append(aa)
    aa=addDir3('[COLOR lightblue]CBS[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=16&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://cdn.freebiesupply.com/logos/large/2x/cbs-logo-png-transparent.png','https://tvseriesfinale.com/wp-content/uploads/2014/10/cbs40-590x221.jpg','HBO')
    all_d.append(aa)
    aa=addDir3('[COLOR purple]SyFy[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=77&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'http://cdn.collider.com/wp-content/uploads/syfy-logo1.jpg','https://imagesvc.timeincapp.com/v3/mm/image?url=https%3A%2F%2Fewedit.files.wordpress.com%2F2017%2F05%2Fdefault.jpg&w=1100&c=sc&poi=face&q=85','SyFy')
    all_d.append(aa)
    aa=addDir3('[COLOR lightgreen]The CW[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=71&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://www.broadcastingcable.com/.image/t_share/MTU0Njg3Mjc5MDY1OTk5MzQy/tv-network-logo-cw-resized-bc.jpg','https://i2.wp.com/nerdbastards.com/wp-content/uploads/2016/02/The-CW-Banner.jpg','The CW')
    all_d.append(aa)
    aa=addDir3('[COLOR silver]ABC[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=2&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'http://logok.org/wp-content/uploads/2014/03/abc-gold-logo-880x660.png','https://i.ytimg.com/vi/xSOp4HJTxH4/maxresdefault.jpg','ABC')
    all_d.append(aa)
    aa=addDir3('[COLOR yellow]NBC[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=6&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://designobserver.com/media/images/mondrian/39684-NBC_logo_m.jpg','https://www.nbcstore.com/media/catalog/product/cache/1/image/1000x/040ec09b1e35df139433887a97daa66f/n/b/nbc_logo_black_totebagrollover.jpg','NBC')
    all_d.append(aa)
    aa=addDir3('[COLOR gold]AMAZON[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=1024&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'http://g-ec2.images-amazon.com/images/G/01/social/api-share/amazon_logo_500500._V323939215_.png','https://cdn.images.express.co.uk/img/dynamic/59/590x/Amazon-Fire-TV-Amazon-Fire-TV-users-Amazon-Fire-TV-stream-Amazon-Fire-TV-Free-Dive-TV-channel-Amazon-Fire-TV-news-Amazon-1010042.jpg?r=1535541629130','AMAZON')
    all_d.append(aa)
    aa=addDir3('[COLOR green]hulu[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=453&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://i1.wp.com/thetalkinggeek.com/wp-content/uploads/2012/03/hulu_logo_spiced-up.png?resize=300%2C225&ssl=1','https://www.google.com/url?sa=i&rct=j&q=&esrc=s&source=images&cd=&cad=rja&uact=8&ved=2ahUKEwi677r77IbeAhURNhoKHeXyB-AQjRx6BAgBEAU&url=https%3A%2F%2Fwww.hulu.com%2F&psig=AOvVaw0xW2rhsh4UPsbe8wPjrul1&ust=1539638077261645','hulu')
    all_d.append(aa)
    aa=addDir3('[COLOR red]Showtime[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=67&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://res.cloudinary.com/wnotw/images/c_limit,w_1536,q_auto:best,f_auto/v1501788508/sci5cdawypsux61i9pyb/showtime-networks-logo','https://www.sho.com/site/image-bin/images/0_0_0/0_0_0_prm-ogseries_1280x640.jpg','showtime')
    all_d.append(aa)
    aa=addDir3('[COLOR red]BBC One[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=4&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://lh3.googleusercontent.com/proxy/LnjjtuGk_PErC5iaReOcy6EEvwjT9wzlyZBKhQHconLsyHWdVn1NHa-Bz3E0_Dev0KV_yJtGyQTlHDwvvm3zW3i0NFSmQVim5_hYOeZ-jWpD1Zs','https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/BBC_One_HD.svg/800px-BBC_One_HD.svg.png','BBC')
    all_d.append(aa)
    aa=addDir3('[COLOR teal]BBC Two[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=332&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://pbs.twimg.com/profile_images/1057914504321908736/06hkWvx__400x400.jpg','http://amirsaidani.co.uk/wp-content/uploads/2019/06/BBC_TWO_LOGO_ANIMATION.gif','BBC')
    all_d.append(aa)
    aa=addDir3('[COLOR pink]BBC Three[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=3&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/BBC_Three_%282020%29.svg/1200px-BBC_Three_%282020%29.svg.png','https://ichef.bbci.co.uk/news/1024/media/images/81061000/jpg/_81061920_bbcthreelogo.jpg','BBC')
    all_d.append(aa)
    aa=addDir3('[COLOR lightblue]ITV[/COLOR]',f'https://api.themoviedb.org/3/discover/tv?api_key={tmdb_key}&with_networks=9&language={lang}&sort_by={order_by}&timezone=America%2FNew_York&include_null_first_air_dates=false&page=1',14,'https://sm.imgix.net/20/31/itv.jpg?w=1200&h=1200&auto=compress,format&fit=clip','https://www.imediaethics.org/wp-content/uploads/2018/11/SCfaQb9l_400x400-350x350.jpg','BBC')
    all_d.append(aa)
    
    xbmcplugin .addDirectoryItems(int(sys.argv[1]),all_d,len(all_d))