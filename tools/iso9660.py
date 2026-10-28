"""List and extract files from a MODE2/2352 PlayStation BIN (ISO 9660 on 2048-byte user data)."""
import struct, sys
from pathlib import Path

SECT, DATA_OFF = 2352, 24


class Bin:
    def __init__(self, path):
        self.f = open(path, "rb")

    def sector(self, lba):
        self.f.seek(lba * SECT + DATA_OFF)
        return self.f.read(2048)

    def read(self, lba, size):
        out = bytearray()
        n = (size + 2047) // 2048
        for i in range(n):
            out += self.sector(lba + i)
        return bytes(out[:size])

    def walk(self, lba=None, size=None, prefix=""):
        if lba is None:
            pvd = self.sector(16)
            root = pvd[156:190]
            lba, size = struct.unpack("<I", root[2:6])[0], struct.unpack("<I", root[10:14])[0]
        data = self.read(lba, size)
        i = 0
        while i < len(data):
            ln = data[i]
            if ln == 0:
                i = (i // 2048 + 1) * 2048
                continue
            rec = data[i:i + ln]
            elba, esize, flags, nl = struct.unpack("<I", rec[2:6])[0], struct.unpack("<I", rec[10:14])[0], rec[25], rec[32]
            name = rec[33:33 + nl].decode("latin-1")
            i += ln
            if name in ("\x00", "\x01"):
                continue
            name = name.split(";")[0]
            if flags & 2:
                yield from self.walk(elba, esize, prefix + name + "/")
            else:
                yield prefix + name, elba, esize


if __name__ == "__main__":
    b = Bin(sys.argv[1])
    files = list(b.walk())
    if len(sys.argv) > 3:  # extract files whose path matches a suffix list
        out = Path(sys.argv[2])
        for p, lba, size in files:
            if any(p.upper().endswith(s.upper()) for s in sys.argv[3:]):
                dst = out / p
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(b.read(lba, size))
        print("extracted")
    else:
        for p, lba, size in files:
            print(size, p)
