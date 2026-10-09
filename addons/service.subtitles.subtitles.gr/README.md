
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

All results are Greek. Providers that carry other languages are filtered
before anything reaches your screen.

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
- **Fast repeat searches** via a local result cache (clearable from settings).
- **Fully translated UI** in English and Greek, including help text for
  every setting.

## The two power sources

Subs4Series and SubDL sit behind Cloudflare-grade bot protection that
plain Python requests cannot pass. The addon ships an optional bridge for
them:

1. In settings, run **Install curl_cffi dependency**, then restart Kodi.
2. The Subs4Series and SubDL toggles unlock automatically; enable them.

Subs4Series additionally rate-limits *downloads* behind a captcha. There is
no captcha solver here by design — instead, solve it once in your own
browser and paste the session cookie via **Set session cookie from browser**.
Search keeps working regardless.

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
