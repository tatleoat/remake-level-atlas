"""Decode PlayStation MDEC "BS" v2/v3 frames (Resident Evil 1 .BSS backgrounds: 320x240, one frame per 32 KB).

Usage: bsdecode.py OUT_DIR FILE.BSS [...]  -> OUT_DIR/<name>_<n>.png for every frame in each file.
The bitstream is read as little-endian 16-bit words, most significant bit first; AC codes are MPEG-1 table B.14
with a 6-bit run + 10-bit level escape; v3 codes the DC terms differentially with MPEG-1 DC size codes.
"""
import math, struct, sys
from pathlib import Path
from multiprocessing import Pool
from PIL import Image

AC = """10 EOB|11 0 1|011 1 1|0100 0 2|0101 2 1|00101 0 3|00111 3 1|00110 4 1|000110 1 2|000111 5 1|000101 6 1|000100 7 1|
0000110 0 4|0000100 2 2|0000111 8 1|0000101 9 1|000001 ESC|00100110 0 5|00100001 0 6|00100101 1 3|00100100 3 2|00100111 10 1|
00100011 11 1|00100010 12 1|00100000 13 1|0000001010 0 7|0000001100 1 4|0000001011 2 3|0000001111 4 2|0000001001 5 2|
0000001110 14 1|0000001101 15 1|0000001000 16 1|000000011101 0 8|000000011000 0 9|000000010011 0 10|000000010000 0 11|
000000011011 1 5|000000010100 2 4|000000011100 3 3|000000010010 4 3|000000011110 6 2|000000010101 7 2|000000010001 8 2|
000000011111 17 1|000000011010 18 1|000000011001 19 1|000000010111 20 1|000000010110 21 1|0000000011010 0 12|
0000000011001 0 13|0000000011000 0 14|0000000010111 0 15|0000000010110 1 6|0000000010101 1 7|0000000010100 2 5|
0000000010011 3 4|0000000010010 5 3|0000000010001 9 2|0000000010000 10 2|0000000011111 22 1|0000000011110 23 1|
0000000011101 24 1|0000000011100 25 1|0000000011011 26 1|00000000011111 0 16|00000000011110 0 17|00000000011101 0 18|
00000000011100 0 19|00000000011011 0 20|00000000011010 0 21|00000000011001 0 22|00000000011000 0 23|00000000010111 0 24|
00000000010110 0 25|00000000010101 0 26|00000000010100 0 27|00000000010011 0 28|00000000010010 0 29|00000000010001 0 30|
00000000010000 0 31|000000000011000 0 32|000000000010111 0 33|000000000010110 0 34|000000000010101 0 35|
000000000010100 0 36|000000000010011 0 37|000000000010010 0 38|000000000010001 0 39|000000000010000 0 40|
000000000011111 1 8|000000000011110 1 9|000000000011101 1 10|000000000011100 1 11|000000000011011 1 12|
000000000011010 1 13|000000000011001 1 14|0000000000010011 1 15|0000000000010010 1 16|0000000000010001 1 17|
0000000000010000 1 18|0000000000010100 6 3|0000000000011010 11 2|0000000000011001 12 2|0000000000011000 13 2|
0000000000010111 14 2|0000000000010110 15 2|0000000000010101 16 2|0000000000011111 27 1|0000000000011110 28 1|
0000000000011101 29 1|0000000000011100 30 1|0000000000011011 31 1"""
ACT = {}
for e in AC.replace("\n", "").split("|"):
    p = e.split()
    ACT[(len(p[0]), int(p[0], 2))] = p[1] if len(p) == 2 else (int(p[1]), int(p[2]))
DCL = {(3, 0b100): 0, (2, 0b00): 1, (2, 0b01): 2, (3, 0b101): 3, (3, 0b110): 4, (4, 0b1110): 5, (5, 0b11110): 6,
       (6, 0b111110): 7, (7, 0b1111110): 8}
DCC = {(2, 0b00): 0, (2, 0b01): 1, (2, 0b10): 2, (3, 0b110): 3, (4, 0b1110): 4, (5, 0b11110): 5, (6, 0b111110): 6,
       (7, 0b1111110): 7, (8, 0b11111110): 8}
ZZ = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
      35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55,
      62, 63]
Q = [2, 16, 19, 22, 26, 27, 29, 34, 16, 16, 22, 24, 27, 29, 34, 37, 19, 22, 26, 27, 29, 34, 34, 38, 22, 22, 26, 27, 29, 34,
     37, 40, 22, 26, 27, 29, 32, 35, 40, 48, 26, 27, 29, 32, 35, 40, 48, 58, 26, 27, 29, 34, 38, 46, 56, 69, 27, 29, 35, 38,
     46, 56, 69, 83]
C = [[(math.sqrt(0.5) if u == 0 else 1.0) * math.cos((2 * x + 1) * u * math.pi / 16) / 2 for u in range(8)] for x in range(8)]
BASIS = [[C[y][v] * C[x][u] for y in range(8) for x in range(8)] for v in range(8) for u in range(8)]  # index v*8+u


class Bits:
    def __init__(self, data):
        self.w = struct.unpack("<%dH" % (len(data) // 2), data[:len(data) // 2 * 2])
        self.pos = 0

    def peek(self, n):
        v, p = 0, self.pos
        for _ in range(n):
            wi = p >> 4
            v = (v << 1) | ((self.w[wi] >> (15 - (p & 15))) & 1 if wi < len(self.w) else 0)
            p += 1
        return v

    def get(self, n):
        v = self.peek(n)
        self.pos += n
        return v


def vlc(bits, table, maxlen):
    for n in range(2, maxlen + 1):
        k = (n, bits.peek(n))
        if k in table:
            bits.pos += n
            return table[k]
    raise ValueError("bad code at bit %d" % bits.pos)


def block(bits, version, qscale, pred, comp):
    coef = [0] * 64
    if version >= 3:
        size = vlc(bits, DCL if comp == 2 else DCC, 8)
        diff = 0
        if size:
            diff = bits.get(size)
            if not diff >> (size - 1):
                diff -= (1 << size) - 1
        pred[comp] += diff * 4
        dc = pred[comp]
    else:
        dc = bits.get(10)
        if dc >= 512:
            dc -= 1024
    coef[0] = dc * Q[0]
    i = 0
    while True:
        c = vlc(bits, ACT, 16)
        if c == "EOB":
            break
        if c == "ESC":
            run, lev = bits.get(6), bits.get(10)
            if lev >= 512:
                lev -= 1024
        else:
            run, lev = c
            if bits.get(1):
                lev = -lev
        i += run + 1
        if i > 63:
            raise ValueError("coefficient overflow")
        z = ZZ[i]
        coef[z] = (lev * qscale * Q[z]) // 8
    out = [0.0] * 64
    for k, c in enumerate(coef):
        if c:
            b = BASIS[k]
            for j in range(64):
                out[j] += c * b[j]
    return out


def frame(data, w=320, h=240):
    nwords, magic, qscale, version = struct.unpack("<HHHH", data[:8])
    assert magic == 0x3800, hex(magic)
    bits = Bits(data[8:])
    img = Image.new("RGB", (w, h))
    px = img.load()
    pred = [0, 0, 0]  # Cr, Cb, Y
    for mx in range(w // 16):
        for my in range(h // 16):
            cr = block(bits, version, qscale, pred, 0)
            cb = block(bits, version, qscale, pred, 1)
            ys = [block(bits, version, qscale, pred, 2) for _ in range(4)]
            for yy in range(16):
                for xx in range(16):
                    yv = ys[(yy >> 3) * 2 + (xx >> 3)][(yy & 7) * 8 + (xx & 7)] + 128
                    ci = (yy >> 1) * 8 + (xx >> 1)
                    r_, b_ = cr[ci], cb[ci]
                    px[mx * 16 + xx, my * 16 + yy] = (max(0, min(255, int(yv + 1.402 * r_))),
                                                      max(0, min(255, int(yv - 0.3437 * b_ - 0.7143 * r_))),
                                                      max(0, min(255, int(yv + 1.772 * b_))))
    return img


def decode_file(args):
    out, path = args
    data = Path(path).read_bytes()
    done = []
    for k in range(len(data) // 32768):
        blk = data[k * 32768:(k + 1) * 32768]
        if blk[2:4] != b"\x00\x38":
            continue
        try:
            img = frame(blk)
        except Exception as e:
            print("fail", path, k, e)
            continue
        name = Path(path).stem + "_%d.png" % k
        img.save(Path(out) / name)
        done.append(name)
    return path, done


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    with Pool() as pool:
        for path, done in pool.imap_unordered(decode_file, [(str(out), p) for p in sys.argv[2:]]):
            print(Path(path).name, len(done))
