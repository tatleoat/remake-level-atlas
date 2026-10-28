"""Geometry helpers for the room outlines: label points inside rooms and door points on shared walls."""
import math


def pts(poly):
    return [(poly[i], poly[i + 1]) for i in range(0, len(poly), 2)]


def inside(p, P):
    x, y = p
    c = False
    for i in range(len(P)):
        (x1, y1), (x2, y2) = P[i], P[(i + 1) % len(P)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def edge_dist(p, P):
    return min(seg_dist(p, P[i], P[(i + 1) % len(P)]) for i in range(len(P)))


def label_point(poly):
    """Point inside the polygon farthest from its walls (coarse grid, then refine)."""
    P = pts(poly)
    xs, ys = [p[0] for p in P], [p[1] for p in P]
    best, bd = None, -1
    step = max(1.0, min(max(xs) - min(xs), max(ys) - min(ys)) / 24)
    y = min(ys) + step / 2
    while y < max(ys):
        x = min(xs) + step / 2
        while x < max(xs):
            if inside((x, y), P):
                d = edge_dist((x, y), P)
                if d > bd:
                    best, bd = (x, y), d
            x += step
        y += step
    if best is None:
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    for s in (step / 2, step / 4, step / 8):
        for dx in (-s, 0, s):
            for dy in (-s, 0, s):
                q = (best[0] + dx, best[1] + dy)
                if inside(q, P):
                    d = edge_dist(q, P)
                    if d > bd:
                        best, bd = q, d
    return (round(best[0], 1), round(best[1], 1))


def boundary_samples(P, step=1.0):
    out = []
    for i in range(len(P)):
        (x1, y1), (x2, y2) = P[i], P[(i + 1) % len(P)]
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / step))
        for k in range(n):
            out.append((x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n))
    return out


def door_point(polyA, polyB, tol=3.0):
    """Midpoint of the longest stretch of wall A shares with B; else the midpoint of the closest approach."""
    A, B = pts(polyA), pts(polyB)
    S = boundary_samples(A)
    near = [edge_dist(p, B) <= tol for p in S]
    runs, cur = [], []
    for p, ok in zip(S + S[:1], near + near[:1]):
        if ok:
            cur.append(p)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if runs:
        r = max(runs, key=len)
        m = r[len(r) // 2]
        return (round(m[0], 1), round(m[1], 1)), True
    best = min(((edge_dist(p, B), p) for p in S))
    p = best[1]
    SB = boundary_samples(B)
    q = min(SB, key=lambda s: math.hypot(s[0] - p[0], s[1] - p[1]))
    return (round((p[0] + q[0]) / 2, 1), round((p[1] + q[1]) / 2, 1)), False


def area(poly):
    P = pts(poly)
    return abs(sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))) / 2
