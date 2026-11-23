import struct
import zlib

from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1

FRAME = bytes([0xFF, 0xFB, 0x90, 0x00]) + bytes(413)


def make_png():
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pixel = zlib.compress(b"\x00\xff\x00\x00")
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", pixel) + chunk(b"IEND", b""))


def make_mp3(path, title=None, artist=None, album=None, cover=None, frames=200):
    path.write_bytes(FRAME * frames)
    if not (title or artist or album or cover):
        return path
    tags = ID3()
    if title:
        tags.add(TIT2(encoding=3, text=title))
    if artist:
        tags.add(TPE1(encoding=3, text=artist))
    if album:
        tags.add(TALB(encoding=3, text=album))
    if cover:
        tags.add(APIC(encoding=3, mime="image/png", type=3, desc="", data=cover))
    tags.save(path)
    return path
