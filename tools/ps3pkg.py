"""List or extract files from a PS3 retail .pkg (AES-128-CTR with the published PS3 package key).

Usage: ps3pkg.py PKG list > files.tsv
       ps3pkg.py PKG extract OUT_DIR SUBSTRING [...]   (files whose path contains any substring)
"""
import struct, sys
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PS3_KEY = bytes.fromhex("2E7B71D7C9C9A14EA3221F188828B8F8")


class Pkg:
    def __init__(self, path):
        self.f = open(path, "rb")
        h = self.f.read(0x80)
        assert h[:4] == b"\x7fPKG", h[:4]
        self.rev, self.typ = struct.unpack(">HH", h[4:8])
        self.items = struct.unpack(">I", h[0x14:0x18])[0]
        self.data_off, self.data_size = struct.unpack(">QQ", h[0x20:0x30])
        self.content_id = h[0x30:0x60].rstrip(b"\0").decode()
        self.riv = int.from_bytes(h[0x70:0x80], "big")

    def dec(self, off, size):
        """Decrypt `size` bytes at `off` within the data area."""
        start = off - off % 16
        ctr = (self.riv + start // 16) % (1 << 128)
        c = Cipher(algorithms.AES(PS3_KEY), modes.CTR(ctr.to_bytes(16, "big"))).decryptor()
        self.f.seek(self.data_off + start)
        raw = self.f.read(size + off % 16)
        return c.update(raw)[off % 16:off % 16 + size]

    def entries(self):
        tab = self.dec(0, self.items * 32)
        for i in range(self.items):
            no, ns, do, ds, flags, _ = struct.unpack(">IIQQII", tab[i * 32:i * 32 + 32])
            name = self.dec(no, ns).decode("latin-1")
            yield name, do, ds, flags

    def extract(self, do, ds, dst, chunk=1 << 24):
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "wb") as out:
            p = 0
            while p < ds:
                n = min(chunk, ds - p)
                out.write(self.dec(do + p, n))
                p += n


if __name__ == "__main__":
    pkg = Pkg(sys.argv[1])
    if sys.argv[2] == "list":
        print(f"# {pkg.content_id} rev {pkg.rev:#x} type {pkg.typ} items {pkg.items}")
        for name, do, ds, flags in pkg.entries():
            print(f"{flags & 0xff:#04x}\t{ds}\t{name}")
    else:
        out = Path(sys.argv[3])
        for name, do, ds, flags in pkg.entries():
            if flags & 0xff != 0x04 and any(s in name for s in sys.argv[4:]):
                pkg.extract(do, ds, out / name)
                print(ds, name)
