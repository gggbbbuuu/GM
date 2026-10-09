# E-Radio addon for Kodi

**Developer:** Twilight0 (credits to **lambda** for the original code)

Tune in to Greek radio and listen live. E-Radio gives you browsable access to
1000+ Greek stations aggregated by [e-radio.gr](https://www.e-radio.gr/),
plus a curated list of external stations maintained by the developer.

> This addon is not published nor endorsed by e-radio.gr.

---

## Features

### Browse

| Menu | What it shows |
|---|---|
| All | Every station in the e-radio database (1000+) |
| Trending | Currently trending stations |
| Popular | Top-20 most popular stations |
| Latest | Most recently added stations |
| Categories | Stations grouped by genre (e.g. Greek hits, Rock, News, Sports) |
| Regions | Stations grouped by area (Athens, Thessaloniki, …) plus **Internet Radios** |
| Bookmarks | Your saved stations |
| Search | Fuzzy search across all stations |

### Search

Type part of a station name — Greek or Latin, accents optional — and the addon
returns the 10 closest matches (70% similarity threshold). Matching is
accent-insensitive, so `ment` finds `Μέντα 88`. Duplicate station names are
resolved to the correct entry.

### Bookmarks

Every station listing offers **Add to bookmarks** from the context menu, and
every bookmark offers **Remove from bookmarks**. Bookmarks are sorted by title
and play with one click.

### Developer picks

A small curated list of stations outside e-radio's database (diaspora and
independent radios) is merged into the **Internet Radios** region and into
search results. The list is hosted as JSON in a
[gist](https://gist.github.com/Twilight0/f74c12af7c572fac716f9d3b9e05f569),
so stations can be added, fixed or disabled without an addon update — each
entry carries an `"enable": "1"` / `"0"` flag:

```json
{
    "stations": [
        {
            "enable": "1",
            "name": "Montreal Greek Radio",
            "logo": "https://…/montreal-greek-radio.png",
            "url": "http://live.greekradio.ca:8000/live",
            "genre": null
        }
    ]
}
```

### Playback

Selecting a station resolves its live stream URL on demand:

- The stream protocol (`http`/`https`) advertised by the station is honored,
  so encrypted and plain streams both play.
- Scheme-less, absolute and protocol-relative URLs are all normalized.
- Station artwork is shown where available (high-resolution variant
  preferred); stations without artwork fall back to the addon icon.

### Caching and maintenance

Listings, directory indexes and resolved streams are cached for 6 hours, so
repeat visits are instant and light on the source servers. The cache is
versioned internally — addon updates never serve stale listings.

Every menu carries a **Clear function cache** context-menu entry to force a
fresh fetch at any time (handy after the developer-picks list changes).

---

## Requirements

- Kodi 19 (Matrix) or newer — Python 3 (`xbmc.python` 3.0.0)
- `script.module.tulip` 4.1.2
- `script.module.urldispatcher` 1.1.0
- `script.module.netclient` 1.1.2
- `script.module.unicache` 1.0.0
- `script.module.fuzzywuzzy` 0.17.0

All dependencies resolve automatically when installing from the
[Twilight0 repository](https://github.com/Twilight0/repository.twilight0).

---

## Installation

1. Add the Twilight0 repository as a Kodi file source and install
   `repository.twilight0` from the zip.
2. From *Add-ons → Install from repository → Twilight0 Repository →
   Music add-ons*, install **E-Radio**.
3. Open it from *Music → Add-ons → E-Radio*.

To install manually, zip the addon folder and use
*Add-ons → Install from zip file* (dependencies must then be installed
separately).

---

## Usage tips

- Lists are sortable by title via Kodi's sort control.
- Streams open in Kodi's music player, so visualisations, now-playing
  info and remote-control apps work as usual.
- If a station fails to play, try again later — source streams go up and
  down; persistent failures can be reported on the
  [issue tracker](https://github.com/Twilight0/plugin.audio.eradio.gr/issues).

---

## Artwork

Addon artwork sourced from public domains:

- http://ecx.images-amazon.com/images/I/41OhtJ5A0BL.png
- http://www.iconarchive.com/show/windows-8-icons-by-icons8.html

Station logos are provided by e-radio.gr / the respective stations.

---

## License

This software is released under the [GPL 3.0 license][1].

[1]: http://www.gnu.org/licenses/gpl-3.0.html
