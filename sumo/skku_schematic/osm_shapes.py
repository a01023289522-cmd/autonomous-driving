"""OSM 실제 도로선을 읽어 엣지 shape(꺾이는 점 목록)를 만든다.

도로 연결 구조(노드·엣지)는 build_schematic.py에서 직접 정의하고, 모양만 실제 도로를 따른다.
  path_shape(a, b, names=..., highways=...) : a→b 사이 실제 도로선 (이름/종류로 걸러낸 OSM 길에서 최단 경로)
좌표는 build_schematic.py와 같은 평면 좌표 (원점 = 성대역 사거리, m).
"""
import heapq
import math
import os
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OSM_FILES = [os.path.join(HERE, "..", "skku_area", "skku.osm.xml"),   # 성대역 · 학교 (2026-10 OSM API)
             os.path.join(HERE, "skku_se.osm.xml"),                   # 학교 남동쪽 ~ 정천지하차도
             os.path.join(HERE, "skku_ne.osm.xml")]                   # 철길 너머 동쪽 (롯데마트 · 한라비발디)
LAT0, LON0 = 37.30055, 126.97268     # 성대역 사거리
SIMPLIFY = 3.0                       # 단순화 허용 오차 (m): 이보다 작은 굽음은 펴서 직선으로
_DATA = None


def lonlat_xy(lat, lon):
    return ((lon - LON0) * math.cos(math.radians(LAT0)) * 111320, (lat - LAT0) * 110574)


def _load():
    global _DATA
    if _DATA is None:
        pos, ways = {}, {}
        for f in OSM_FILES:
            root = ET.parse(f).getroot()
            pos.update({n.get("id"): lonlat_xy(float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")})
            for w in root.findall("way"):
                tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
                if "highway" in tags or "railway" in tags:
                    ways[w.get("id")] = (tags, [r.get("ref") for r in w.findall("nd")])
        ways = [(t, [r for r in refs if r in pos]) for t, refs in ways.values()]
        _DATA = (pos, [w for w in ways if "highway" in w[0]], [w for w in ways if "railway" in w[0]])
    return _DATA


def rail_lines(box):
    """box = (x0, y0, x1, y1) 안을 지나는 철길(1호선) 선들."""
    pos, _, rails = _load()
    out = []
    for tags, refs in rails:
        if tags.get("railway") != "rail" or tags.get("service"):
            continue
        pts = [pos[r] for r in refs if box[0] < pos[r][0] < box[2] and box[1] < pos[r][1] < box[3]]
        if len(pts) > 1:
            out.append(_rdp(pts, 2.0))
    return out


def _rdp(pts, tol):
    if len(pts) < 3:
        return pts
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    L = math.hypot(x1 - x0, y1 - y0) or 1e-9
    d = [abs((x1 - x0) * (y0 - y) - (x0 - x) * (y1 - y0)) / L for x, y in pts[1:-1]]
    i = max(range(len(d)), key=d.__getitem__)
    if d[i] <= tol:
        return [pts[0], pts[-1]]
    return _rdp(pts[:i + 2], tol)[:-1] + _rdp(pts[i + 1:], tol)


def path_shape(a, b, names=None, highways=None, max_ratio=1.6, snap=45):
    """a, b = (x, y). 조건에 맞는 OSM 길들로 그래프를 만들고 a, b에 가장 가까운 점 사이 최단 경로를 돌려준다.
    못 찾거나 경로가 직선보다 max_ratio배 넘게 길면 None (→ 호출 쪽에서 직선 사용)."""
    pos, ways, _ = _load()
    adj = {}
    for tags, refs in ways:
        if names and tags.get("name") not in names:
            continue
        if highways and tags.get("highway") not in highways:
            continue
        for u, v in zip(refs, refs[1:]):
            d = math.dist(pos[u], pos[v])
            adj.setdefault(u, []).append((v, d))
            adj.setdefault(v, []).append((u, d))
    if not adj:
        return None
    near = lambda p: min(adj, key=lambda n: math.dist(pos[n], p))
    s, t = near(a), near(b)
    if math.dist(pos[s], a) > snap or math.dist(pos[t], b) > snap or s == t:
        return None
    dist, prev, q = {s: 0.0}, {}, [(0.0, s)]
    while q:
        d, u = heapq.heappop(q)
        if u == t:
            break
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            if d + w < dist.get(v, 1e18):
                dist[v], prev[v] = d + w, u
                heapq.heappush(q, (d + w, v))
    if t not in dist or dist[t] > max_ratio * math.dist(a, b) + 30:
        return None
    chain = [t]
    while chain[-1] != s:
        chain.append(prev[chain[-1]])
    pts = [pos[n] for n in reversed(chain)]
    pts = [a] + pts[1:-1] + [b]                  # 양 끝은 우리 노드 위치에 맞춘다
    return _rdp(pts, SIMPLIFY)


# ── 폴리라인 도구 (고가 구간 가운데선) ──
def poly_len(pts):
    return sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))


def project(pts, p):
    """p를 폴리라인에 투영했을 때의 누적 거리."""
    best, acc = (1e18, 0.0), 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        t = max(0.0, min(1.0, ((p[0] - x0) * (x1 - x0) + (p[1] - y0) * (y1 - y0)) / (L * L)))
        q = (x0 + t * (x1 - x0), y0 + t * (y1 - y0))
        d = math.dist(p, q)
        if d < best[0]:
            best = (d, acc + t * L)
        acc += L
    return best[1]


def point_at(pts, s):
    acc = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        if acc + L >= s:
            t = (s - acc) / L
            return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))
        acc += L
    return pts[-1]


def sub(pts, s0, s1):
    """누적 거리 s0~s1 구간 (s0 > s1이면 거꾸로)."""
    if s0 > s1:
        return list(reversed(sub(pts, s1, s0)))
    out, acc = [point_at(pts, s0)], 0.0
    for p, q in zip(pts, pts[1:]):
        acc += math.dist(p, q)
        if s0 < acc < s1:
            out.append(q)
    out.append(point_at(pts, s1))
    return out


def offset(pts, d):
    """진행 방향 오른쪽으로 d만큼 평행 이동 (꺾이는 점은 양쪽 법선의 평균)."""
    out = []
    for i, (x, y) in enumerate(pts):
        nx = ny = 0.0
        for (ax, ay), (bx, by) in ((pts[max(i - 1, 0)], pts[i]), (pts[i], pts[min(i + 1, len(pts) - 1)])):
            L = math.hypot(bx - ax, by - ay)
            if L > 0:
                nx, ny = nx + (by - ay) / L, ny - (bx - ax) / L
        n = math.hypot(nx, ny) or 1.0
        out.append((x + nx / n * d, y + ny / n * d))
    return out
