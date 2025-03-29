import time
import xbmc
import os
import xbmcgui
import urllib.request, urllib.error, urllib.parse
import webbrowser


def menuoptions():
    dialog = xbmcgui.Dialog()
    funcs = (
        function1,
        function2,
        function3,
        function4,
        function5,
        function6,
        function7,
        function8,
        function9,
        function10,
        function11,
        function12,
        function13,
        function14,
        function15,
        function16
        )
        
    call = dialog.select('[B][COLOR=blue]GKoBu Pair-ing System[/COLOR][/B]', [
    '[B][COLOR=yellow] **** Common sites to login **** [/COLOR][/B]', 
    '[B][COLOR=blue]      Uptobox.com[/COLOR][/B]',
    '[B][COLOR=blue]      Streamzz.to ip deblock[/COLOR][/B]',
    '[B][COLOR=blue]      vShare.eu[/COLOR][/B]',
    '[B][COLOR=blue]      Sign For Real Debrid[/COLOR][/B]',
    '[B][COLOR=blue]      Sign For Alldebrid[/COLOR][/B]',
    '[B][COLOR=blue]      Sign For Premiumize.me[/COLOR][/B]',
    '[B][COLOR=blue]      Ororo Tv[/COLOR][/B]',
    '[B][COLOR=blue]      Trakt Tv[/COLOR][/B]',
    '[B][COLOR=blue]      Tmdb[/COLOR][/B]',
    '[B][COLOR=blue]      Stremlord[/COLOR][/B]',
    '[B][COLOR=blue]      Imdb[/COLOR][/B]',
    '[B][COLOR=yellow] **** Sports Schedule Sites **** [/COLOR][/B]',
    '[B][COLOR=lime]      sport-tv-guide.live[/COLOR][/B]',
    '[B][COLOR=lime]      livesoccertv.com[/COLOR][/B]',
    '[B][COLOR=lime]      sporteventz.com[/COLOR][/B]'])
    # dialog.selectreturns
    #   0 -> escape pressed
    #   1 -> first item
    #   2 -> second item
    if call:
        # esc is not pressed
        if call < 0:
            return
        func = funcs[call-16]
        return func()
    else:
        func = funcs[call]
        return func()
    return 

def platform():
    if xbmc.getCondVisibility('system.platform.android'):
        return 'android'
    elif xbmc.getCondVisibility('system.platform.linux'):
        return 'linux'
    elif xbmc.getCondVisibility('system.platform.windows'):
        return 'windows'
    elif xbmc.getCondVisibility('system.platform.osx'):
        return 'osx'
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return 'atv2'
    elif xbmc.getCondVisibility('system.platform.ios'):
        return 'ios'

myplatform = platform()

def function1(): 0

def function2():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://uptobox.com/pin' ) )
    else:
        opensite = webbrowser . open('https://uptobox.com/pin')
        
def function3():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://streamzz.to/fcnk0bjhianZxNGJiZXgw' ) )
    else:
        opensite = webbrowser . open('https://streamzz.to/fcnk0bjhianZxNGJiZXgw')
        
def function4():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'http://vshare.eu/pair' ) )
    else:
        opensite = webbrowser . open('http://vshare.eu/pair')       
        
def function5():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://real-debrid.com' ) )
    else:
        opensite = webbrowser . open('https://real-debrid.com/')
        
def function6():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://alldebrid.com/register/' ) )
    else:
        opensite = webbrowser . open('https://alldebrid.com/register/')  

def function7():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://www.premiumize.me/login' ) )
    else:
        opensite = webbrowser . open('https://www.premiumize.me/login')

def function8():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://ororo.tv/en/users/sign_up' ) )
    else:
        opensite = webbrowser . open('https://ororo.tv/en/users/sign_up')

def function9():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://trakt.tv/join' ) )
    else:
        opensite = webbrowser . open('https://trakt.tv/join')

def function10():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://www.themoviedb.org/account/signup' ) )
    else:
        opensite = webbrowser . open('https://www.themoviedb.org/account/signup')

def function11():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'http://www.streamlord.com/register.html' ) )
    else:
        opensite = webbrowser . open('http://www.streamlord.com/register.html')

def function12():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://m.imdb.com/ap/register?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.imdb.com%2Fap-signin-handler&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=imdb_mobile_web_us&openid.mode=checkid_setup&siteState=eyJvcGVuaWQuYXNzb2NfaGFuZGxlIjoiaW1kYl9tb2JpbGVfd2ViX3VzIiwicmVkaXJlY3RUbyI6Imh0dHA6Ly9tLmltZGIuY29tLz9yZWZfPW1fbG9naW4ifQ&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&&tag=imdbtag_reg-20' ) )
    else:
        opensite = webbrowser . open('https://m.imdb.com/ap/register?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.imdb.com%2Fap-signin-handler&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=imdb_mobile_web_us&openid.mode=checkid_setup&siteState=eyJvcGVuaWQuYXNzb2NfaGFuZGxlIjoiaW1kYl9tb2JpbGVfd2ViX3VzIiwicmVkaXJlY3RUbyI6Imh0dHA6Ly9tLmltZGIuY29tLz9yZWZfPW1fbG9naW4ifQ&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&&tag=imdbtag_reg-20')        
        
 
def function13(): 0

def function14():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://sport-tv-guide.live/el/' ) )
    else:
        opensite = webbrowser . open('https://sport-tv-guide.live/el/')

def function15():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://www.livesoccertv.com/schedules/' ) )
    else:
        opensite = webbrowser . open('https://www.livesoccertv.com/schedules/')

def function16():
    if myplatform == 'android': # Android 
        opensite = xbmc.executebuiltin( 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % ( 'https://sporteventz.com/en/' ) )
    else:
        opensite = webbrowser . open('https://sporteventz.com/en/') 


menuoptions()
