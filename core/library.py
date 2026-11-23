import os
from pathlib import Path

from core.tags import read_tags

MP3_SUFFIX = ".mp3"


def find_mp3_files(folder):
    return sorted(
        path for path in Path(folder).rglob("*") if path.suffix.lower() == MP3_SUFFIX
    )


def add_files_to_library(db, paths):
    ids, skipped = [], []
    for path in paths:
        path = os.path.normpath(os.path.abspath(path))
        if not os.path.isfile(path) or not path.lower().endswith(MP3_SUFFIX):
            skipped.append(path)
            continue
        ids.append(db.add_track(path, **read_tags(path)))
    return ids, skipped
