import csv
from pathlib import Path

CSV_HEADER = ["Название", "Исполнитель", "Альбом", "Длительность (сек)", "Путь"]
CSV_DELIMITER = ";"
TXT_ENCODINGS = ("utf-8-sig", "cp1251")


def export_playlist_csv(file_path, tracks):
    with open(file_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=CSV_DELIMITER)
        writer.writerow(CSV_HEADER)
        for track in tracks:
            writer.writerow([
                track["title"],
                track["artist"],
                track["album"] or "",
                track["duration_sec"],
                track["path"],
            ])
    return len(tracks)


def read_paths_txt(file_path):
    text = _read_text(file_path)
    paths = []
    for line in text.splitlines():
        line = line.strip().strip('"')
        if line and not line.startswith("#"):
            paths.append(line)
    return paths


def _read_text(file_path):
    raw = Path(file_path).read_bytes()
    for encoding in TXT_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")
