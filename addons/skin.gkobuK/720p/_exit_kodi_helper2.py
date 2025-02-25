import os, xbmc, xbmcgui
DIALOG         = xbmcgui.Dialog()
COLOR1         = 'white'
COLOR2         = 'white'

choice = DIALOG.yesno('Άμεση διακοπή συστήματος', '[COLOR %s]Το σύστημα θα κλείσει άμεσα...[CR]Θέλετε να συνεχίσετε?[/COLOR]' % COLOR2, nolabel='[B][COLOR white] Όχι, Άκυρο[/COLOR][/B]',yeslabel='[B][COLOR white]Ναι, κλείσε[/COLOR][/B]')
if choice == 1:
    os._exit(1)
else:
    xbmc.executebuiltin("Action(Close)")
