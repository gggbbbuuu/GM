
# Subtitles.gr — Greek subtitles for Kodi

A Kodi subtitle service focused on one thing: finding **Greek subtitles**
for your movies and episodes, across every worthwhile Greek source, in a
single search.

## Sources

| Source | Movies | Series | Notes |
|---|---|---|---|
| GreekSubs.net | ✅ | ✅ | Includes whole-season packs |
| Subs4Free | ✅ | — | Movies; no extra addons needed |
| Subs4Series | — | ✅ | Needs `curl_cffi` (see below) |
| SubDL | ✅ | ✅ | Needs `curl_cffi` (see below) |
| YIFI | ✅ | — | |
| TVsubtitles.net | — | ✅ | |
| Moviesubtitles.org | ✅ | — | |
| Subtitles.gr | ✅ | ✅ | Off by default — site unreachable |

Results are Greek. Sources that also carry other languages are filtered, with
one exception: the opt-in translation fallback, which offers English
subtitles and translates them to Greek when you download them.

## What it does for you

- **One search, every source.** All enabled providers are queried in
  parallel with a live progress dialog naming each source as it answers.
  Stragglers can't freeze the UI: after a timeout you get what arrived.
- **Smart matching.** Results carry ratings, download counts and sync
  probability, and can be sorted by any of them. Subtitles matching your
  exact release are flagged as in sync.
- **Season packs done right.** Where a source offers a whole season in one
  archive, you get the pack *and* the episode file side by side — pick the
  episode from a chooser, or keep the zip. Cancelling the chooser cleanly
  aborts instead of erroring.
- **Correct Greek text.** SubDL serves its subtitles in Windows-1253; they are
  converted to UTF-8 on download, so no mojibake.
- **Hearing-impaired flags** where the source provides them.
- **Captcha-gated sources, without a solver.** Where a site puts a captcha in
  front of a download, Kodi shows a QR code and an address; you solve it in your
  own browser, on your own phone if you like, and the download carries on.
  Nothing is solved or bypassed on your behalf.
- **Fast repeat searches** via a local result cache (clearable from settings).
- **Fully translated UI** in English and Greek, including help text for
  every setting.

## The two power sources

Subs4Series and SubDL sit behind Cloudflare-grade bot protection that
plain Python requests cannot pass. The addon ships an optional bridge for
them:

1. In settings, run **Install curl_cffi dependency**, then restart Kodi.
2. The Subs4Series and SubDL toggles unlock automatically; enable them.

Subs4Series additionally puts a per-request reCAPTCHA in front of *downloads*.
There is no captcha solver here by design, and no cookie can stand in for it:
one token answers one request, once, and it can only be minted in a real browser
on the site's own origin. That is therefore exactly what is asked of you, and
nothing more.

When a download stops at that captcha, a dialog appears carrying the site's
subtitle page, a QR code, and the address of a short-lived listener. Solve the
captcha on that page, then click **Import to Kodi** in your bookmarks bar. The
browser posts the site's own form with the token you just ticked, lands on the
archive, and Kodi finishes the download from there. You solve it, in your own
browser, once per download; nothing is solved or bypassed on your behalf.

The dialog also offers **Open in browser**, which hands the address to a browser
on the same machine. On a set-top box there is no browser to hand it to, and the
QR code is then the whole story: scan it with a phone and the phone does the
solving. The code is drawn as large as the screen allows for exactly that.

### The bookmarklet, and the session cookie

The same listener, the same page and the same bookmarklet also serve the plain
cookie import in settings — **Import session cookie (bookmarklet)** — which is
the easy way to give Kodi your logged-in session without the dev-tools route
below.

Install it once. The page the listener serves has the button to drag to your
bookmarks bar, and here is the same code with your address and token to fill in:
```javascript
javascript:(function(){var u='http://192.168.1.10:50190/set?t=YOUR-TOKEN&c='+encodeURIComponent(document.cookie);var i,f=null,s=document.forms;for(i=0;i<s.length;i++){if(s[i].querySelector('[name="my_recaptcha_challenge_field"]')){f=s[i];break;}}if(!f){window.open(u,'_blank');return;}var t='';try{t=grecaptcha.getResponse();}catch(e){}var b=new URLSearchParams(new FormData(f));b.set('g-recaptcha-response',t);fetch(new URL(f.getAttribute('action')||'',location.href).href,{method:'POST',body:b,credentials:'include'}).then(function(r){location.href=u+'&z='+encodeURIComponent(r.url||'');})['catch'](function(){location.href=u;});})()
```

On a page without that captcha form it simply hands the cookie over; on a page
that has it, it posts the form first and reports where you landed. A bookmarklet
saved by an earlier version only did the first half, so drag it again — the
address and the token are unchanged, only what the bookmarklet does.

**Listener port for cookie import** ships fixed at `50190`, so the address never
changes and the bookmarklet only has to be installed once. Replace
`192.168.1.10:50190` with your Kodi's LAN address and port, and `YOUR-TOKEN`
with the value of **Import token** in settings — or skip the hand-editing and
copy the bookmarklet straight from the listener page, which has your real
address and token filled in. Clear the field only if that port is taken on your
box; then the listener falls back to a free port and says so, and the saved
bookmarklet has to be made again.

No bookmarklets at all: the listener page also offers a **userscript** doing
the same job on its own. Install the Violentmonkey extension once (Firefox on
desktop and Android, Chrome, Vivaldi on Android via the Chrome Web Store), then
open the page's install link in the same browser and confirm. From then on the
page watches for the ticked captcha and hands the subtitle over by itself — the
bookmarklet stays as the fallback for browsers without a script manager
(Chrome desktop included, if you'd rather not install one).

Clearing **Import token** mints a new one on the next run and invalidates every
bookmarklet made before, so that is how you rotate it.

### Import it by hand

Open the bookmarklet page's expander at the bottom. In your browser's developer
tools (F12) go to Network, right click any subs4series request, choose
Copy → Copy as cURL and paste it — the cookie is extracted for you.

### What the listener does and does not do

It binds a port on this device for as long as that dialog is on screen, then
stops — one import and it is gone. A request without the right token is
refused, and the listener never answers where the cookie was asked: it
redirects to a cookie-free page, so the session is not left in your address bar
or in your history. The cookie travels over plain HTTP within your own network,
like any other LAN traffic; nothing is sent anywhere else, and the addon only
ever stores what you handed it.

A gated download's archive address travels the same way, and it is not a secret:
it names a file on the site, it carries no session, and anything holding it can
fetch that file. It only ever reaches Kodi from your own browser, and it is
discarded once the download has been written.

The dialog closes the moment the hand-over lands, because it is modal: a second
it stays up is a second Kodi takes no input and the download it is waiting for
cannot begin. The confirmation does not depend on the listener outliving it —
the tab that handed the download over lands on the confirmation page, and any
other tab of the same address is told by it through the browser's own storage.

## Requirements

- Kodi 20+ (Nexus and up)
- Bundled framework modules: tulip 4, parsers, unicache, netclient,
  fuzzywuzzy (pulled in automatically)
- `script.module.curlcffi` — optional, only for Subs4Series and SubDL

## Notes

This service is only for Greek subtitles. It is not published nor endorsed
by any of the sites supported.

### Artwork

Artwork sourced from public domain:

http://www.subtitles.gr/logo.jpg


### License

This software is released under the [GPL 3.0 license](http://www.gnu.org/licenses/gpl-3.0.html).
