"""Resident Evil HD Remaster (PS3) background extraction: SFH wrapper -> MT Framework ARC -> TEX (DXT1) -> image.

SFH layout (from kapdap's re-cvx-tools HFS.cs, MIT): a 16-byte header, then 0x20000-byte chunks that each end in a
16-byte checksum. ARC (big-endian on PS3): "\\0CRA", u16 version, u16 count, then 80-byte entries (64-byte name,
type hash, compressed size, flags|size, offset); data is zlib. TEX v0x9D: packed header words, DXT1 = format 19/20.
"""
import struct, zlib
from PIL import Image

CHUNK, CHECK = 0x20000, 0x10


def unwrap_sfh(raw):
    if raw[:4] != b"\x00SFH":
        return raw
    out, pos = bytearray(), 16
    while pos < len(raw):
        n = CHUNK - CHECK if pos + CHUNK - CHECK <= len(raw) - CHECK else len(raw) - pos - CHECK
        out += raw[pos:pos + n]
        pos += n + CHECK
    return bytes(out)


def arc_entries(arc):
    magic, ver, cnt = arc[:4], *struct.unpack(">HH", arc[4:8])
    assert magic == b"\x00CRA", magic
    for i in range(cnt):
        e = arc[8 + i * 80:8 + i * 80 + 80]
        name = e[:64].rstrip(b"\0").decode("latin-1")
        h, cs, us, off = struct.unpack(">IIII", e[64:80])
        yield name, h, cs, us, off


def read_entry(arc, cs, off):
    data = arc[off:off + cs]
    return data if data[1:4] == b"XET" else zlib.decompress(data)  # some textures are stored uncompressed


def tex_image(tex):
    assert tex[1:4] == b"XET", tex[:4]
    w1, w2, w3 = struct.unpack(">III", tex[4:16])
    mips, width, height = w2 & 0x3F, (w2 >> 6) & 0x1FFF, (w2 >> 19) & 0x1FFF
    fmt = (w3 >> 8) & 0xFF
    if fmt in (19, 20, 25):  # DXT1
        size = width * height // 2
        n = 1
    elif fmt in (23, 24, 31, 35, 37, 47):  # DXT5
        size = width * height
        n = 3
    else:
        raise ValueError("format %d" % fmt)
    data = tex[len(tex) - size:] if mips == 1 else tex[-size * 4 // 3:][:size]
    return Image.frombuffer("RGBA", (width, height), data, "bcn", n).convert("RGB"), (width, height, fmt, mips)


def backgrounds(raw):
    """Yield (name, image, info) for every base-map texture in an SFH-wrapped scr archive."""
    arc = unwrap_sfh(raw)
    for name, h, cs, us, off in arc_entries(arc):
        if name.endswith("_BM_NOMIP"):
            im, info = tex_image(read_entry(arc, cs, off))
            yield name, im, info
