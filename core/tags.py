from pathlib import Path

from mutagen import MutagenError
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.mp3 import MP3

UNKNOWN_ARTIST = "Неизвестный"
LATIN1_LAST_CODE = 0xFF


def read_tags(path):
    path = Path(path)
    info = {"title": path.stem, "artist": UNKNOWN_ARTIST, "album": "", "duration_sec": 0}
    info["duration_sec"] = _read_duration(path)
    tags = _read_easy_tags(path)
    info["title"] = _first(tags, "title", info["title"])
    info["artist"] = _first(tags, "artist", UNKNOWN_ARTIST)
    info["album"] = _first(tags, "album", "")
    return info


def read_cover(path):
    try:
        frames = ID3(path).getall("APIC")
    except (MutagenError, OSError):
        return None
    return frames[0].data if frames else None


def fix_encoding(text):
    if any(ord(ch) > LATIN1_LAST_CODE for ch in text) or _has_ascii_letters(text):
        return text
    try:
        fixed = text.encode("latin-1").decode("cp1251")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return fixed if any("а" <= ch.lower() <= "я" for ch in fixed) else text


def _has_ascii_letters(text):
    return any(ch.isascii() and ch.isalpha() for ch in text)


def _read_duration(path):
    try:
        return int(MP3(path).info.length)
    except (MutagenError, OSError):
        return 0


def _read_easy_tags(path):
    try:
        return EasyID3(path)
    except (MutagenError, OSError):
        return {}


def _first(tags, key, default):
    values = tags.get(key)
    if not values or not values[0].strip():
        return default
    return fix_encoding(values[0].strip())
