"""Temporarily apply per-catalog Kodi locale settings during Seren playback."""

import json
from functools import lru_cache

import xbmc

from resources.lib.modules.catalog_profiles import normalize_catalog
from resources.lib.modules.globals import g

KODI_AUDIO_SETTING = "locale.audiolanguage"
KODI_SUBTITLE_SETTING = "locale.subtitlelanguage"

DEFAULT_AUDIO = "mediadefault"
DEFAULT_SUBTITLE = "original"

BACKUP_SETTING = "playback.locale.backup"

AUDIO_SPECIAL = (
    ("mediadefault", 307),
    ("original", 308),
    ("default", 309),
)

SUBTITLE_SPECIAL = (
    ("none", 231),
    ("forced_only", 13207),
    ("original", 308),
    ("default", 309),
)

ISO639_1_CODES = (
    "aa", "ab", "ae", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az", "ba", "be", "bg", "bh", "bi", "bm", "bn",
    "bo", "br", "bs", "ca", "ce", "ch", "co", "cr", "cs", "cu", "cv", "cy", "da", "de", "dv", "dz", "ee", "el", "en",
    "eo", "es", "et", "eu", "fa", "ff", "fi", "fj", "fo", "fr", "fy", "ga", "gd", "gl", "gn", "gu", "gv", "ha", "he",
    "hi", "ho", "hr", "ht", "hu", "hy", "hz", "ia", "id", "ie", "ig", "ii", "ik", "io", "is", "it", "iu", "ja", "jv",
    "ka", "kg", "ki", "kj", "kk", "kl", "km", "kn", "ko", "kr", "ks", "ku", "kv", "kw", "ky", "la", "lb", "lg", "li",
    "ln", "lo", "lt", "lu", "lv", "mg", "mh", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "na", "nb", "nd", "ne",
    "ng", "nl", "nn", "no", "nr", "nv", "ny", "oc", "oj", "om", "or", "os", "pa", "pi", "pl", "ps", "pt", "qu", "rm",
    "rn", "ro", "ru", "rw", "sa", "sc", "sd", "se", "sg", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "ss", "st",
    "su", "sv", "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "ts", "tt", "tw", "ty", "ug", "uk",
    "ur", "uz", "ve", "vi", "vo", "wa", "wo", "xh", "yi", "yo", "za", "zh", "zu",
)


def _use_kodi_key(catalog):
    return f"playback.locale.usekodi.{normalize_catalog(catalog)}"


def _audio_key(catalog):
    return f"playback.audiolanguage.{normalize_catalog(catalog)}"


def _subtitle_key(catalog):
    return f"playback.subtitlelanguage.{normalize_catalog(catalog)}"


def _kodi_core_string(message_id):
    return g.get_language_string(message_id, addon=False)


@lru_cache(maxsize=1)
def _stream_language_pairs():
    """(code, name) pairs for every ISO 639-1 code Kodi can resolve to a display
    name, deduped by name and sorted by name. Shared by _stream_language_names()
    (names only, for the subtitle/audio pickers) and manual_calendar_filter.
    choose_language() (needs the code too, to persist calendar.language)."""
    pairs = []
    seen = set()
    for code in ISO639_1_CODES:
        try:
            name = xbmc.convertLanguage(code, xbmc.ENGLISH_NAME)
        except Exception:
            continue
        if not name or name in seen:
            continue
        seen.add(name)
        pairs.append((code, name))
    pairs.sort(key=lambda pair: pair[1].casefold())
    return tuple(pairs)


@lru_cache(maxsize=1)
def _stream_language_names():
    return tuple(name for _code, name in _stream_language_pairs())


def _special_options(kind):
    special = AUDIO_SPECIAL if kind == "audio" else SUBTITLE_SPECIAL
    return tuple((_kodi_core_string(message_id), value) for value, message_id in special)


def language_options(kind):
    """Return (label, stored value) pairs matching Kodi locale language pickers."""
    options = list(_special_options(kind))
    options.extend((name, name) for name in _stream_language_names())
    return tuple(options)


def get_catalog_audio(catalog):
    return g.get_setting(_audio_key(catalog), DEFAULT_AUDIO) or DEFAULT_AUDIO


def get_catalog_subtitle(catalog):
    return g.get_setting(_subtitle_key(catalog), DEFAULT_SUBTITLE) or DEFAULT_SUBTITLE


def set_use_kodi_defaults(catalog, enabled):
    g.set_setting(_use_kodi_key(catalog), bool(enabled))


def set_catalog_audio(catalog, value):
    g.set_setting(_audio_key(catalog), value)


def set_catalog_subtitle(catalog, value):
    g.set_setting(_subtitle_key(catalog), value)


def reset_catalog_locale(catalog):
    catalog = normalize_catalog(catalog)
    set_use_kodi_defaults(catalog, True)
    set_catalog_audio(catalog, DEFAULT_AUDIO)
    set_catalog_subtitle(catalog, DEFAULT_SUBTITLE)


def uses_kodi_defaults(catalog):
    return g.get_bool_setting(_use_kodi_key(catalog), True)


def resolve_catalog_locale(catalog):
    """Return (audio, subtitle) Kodi setting values for catalog, or None to skip override."""
    catalog = normalize_catalog(catalog)
    if uses_kodi_defaults(catalog):
        return None
    audio = g.get_setting(_audio_key(catalog), DEFAULT_AUDIO) or DEFAULT_AUDIO
    subtitle = g.get_setting(_subtitle_key(catalog), DEFAULT_SUBTITLE) or DEFAULT_SUBTITLE
    return audio, subtitle


def get_kodi_setting_value(setting_id):
    result = g.json_rpc("Settings.GetSettingValue", {"setting": setting_id})
    if not isinstance(result, dict):
        return None
    value = result.get("value")
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)


def set_kodi_setting_value(setting_id, value):
    if value is None:
        return False
    result = g.json_rpc("Settings.SetSettingValue", {"setting": setting_id, "value": value})
    if result is True:
        return True
    if isinstance(result, dict) and result.get("success") is True:
        return True
    return bool(result)


def _persist_backup(backup):
    g.set_setting(BACKUP_SETTING, json.dumps(backup) if backup else "")


def load_orphaned_backup():
    """Return a pending locale backup left behind by an unclean shutdown, or None."""
    raw = g.get_setting(BACKUP_SETTING)
    if not raw:
        return None
    try:
        backup = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return backup if isinstance(backup, dict) else None


def apply_catalog_locale(catalog):
    """Snapshot Kodi locale settings, persist the snapshot, and apply per-catalog overrides.

    Returns the backup dict to pass to restore_catalog_locale() later, or None if
    no override was needed (catalog uses Kodi defaults, or Kodi already matched).
    """
    # Self-healing: if a prior override was never cleanly restored (crash mid-playback,
    # before service.py's startup recovery ran), Kodi's current locale settings are still
    # the OVERRIDDEN values, not the user's real original. Recover them first, or the
    # snapshot below would persist the overridden values as the new "original" and the
    # user's real setting is lost permanently.
    orphaned = load_orphaned_backup()
    if orphaned is not None:
        restore_catalog_locale(orphaned)

    locale = resolve_catalog_locale(catalog)
    if locale is None:
        return None

    audio_value, subtitle_value = locale
    backup = {
        KODI_AUDIO_SETTING: get_kodi_setting_value(KODI_AUDIO_SETTING),
        KODI_SUBTITLE_SETTING: get_kodi_setting_value(KODI_SUBTITLE_SETTING),
        "_catalog": normalize_catalog(catalog),
    }

    if backup[KODI_AUDIO_SETTING] == audio_value and backup[KODI_SUBTITLE_SETTING] == subtitle_value:
        g.log(f"Locale playback: catalog={backup['_catalog']} already matches Kodi settings", "debug")
        return None

    # Persist before mutating global Kodi settings, so a mid-write crash still leaves
    # a recoverable record for service.py's startup orphan check.
    _persist_backup(backup)

    audio_ok = set_kodi_setting_value(KODI_AUDIO_SETTING, audio_value)
    subtitle_ok = set_kodi_setting_value(KODI_SUBTITLE_SETTING, subtitle_value)
    if not audio_ok or not subtitle_ok:
        g.log(
            f"Locale playback: failed to apply catalog={backup['_catalog']} "
            f"(audio={audio_ok}, subtitle={subtitle_ok})",
            "warning",
        )
        restore_catalog_locale(backup)
        return None

    g.log(
        f"Locale playback: catalog={backup['_catalog']} audio={audio_value!r} subtitle={subtitle_value!r}",
        "debug",
    )
    return backup


def restore_catalog_locale(backup):
    """Restore Kodi locale settings from a backup created by apply_catalog_locale."""
    if not backup:
        return

    audio_value = backup.get(KODI_AUDIO_SETTING)
    subtitle_value = backup.get(KODI_SUBTITLE_SETTING)
    if audio_value is not None:
        set_kodi_setting_value(KODI_AUDIO_SETTING, audio_value)
    if subtitle_value is not None:
        set_kodi_setting_value(KODI_SUBTITLE_SETTING, subtitle_value)

    _persist_backup(None)
    g.log(f"Locale playback: restored Kodi settings after catalog={backup.get('_catalog')}", "debug")


def recover_orphaned_locale_override():
    """Restore Kodi locale settings left overridden by an unclean shutdown mid-playback.

    Call once from service.py startup. Idempotent — a second call finds nothing to do,
    since restore_catalog_locale() clears the persisted backup after restoring.
    """
    backup = load_orphaned_backup()
    if backup is None:
        return
    g.log(f"Locale playback: recovering orphaned override for catalog={backup.get('_catalog')}", "warning")
    restore_catalog_locale(backup)
