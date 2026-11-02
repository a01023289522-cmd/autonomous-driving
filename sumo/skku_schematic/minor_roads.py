"""구현 범위 안의 골목·생활도로를 OSM에서 가져와 직접 정의한 핵심 도로에 붙인다.

핵심 도로(서부로 고가 구간, 사거리, 덕영대로, 화산로, 일월로, 교내 순환로 등)는 build_schematic.py에서 정의하고,
나머지 길(residential·unclassified·living_street·tertiary)은 여기서 자동으로 만든다.
  - OSM 길을 교차점마다 나눠 엣지로 만들고, 일방통행(oneway)은 한 방향만 만든다.
  - 핵심 도로와 만나는 끝점은 가까운 핵심 노드(25m 이내)에 붙이고, 없으면 핵심 도로 엣지를 그 자리에서 나눠 붙인다.
    고가 구간 지상도로는 방향마다 따로 있는 일방통행이라, 서쪽 골목은 남쪽 방향에만, 동쪽 골목은 북쪽 방향에만 붙는다.
    중앙분리대가 있는 큰길(divided)도 같은 방식: 골목이 있는 쪽 방향에만 붙어 우회전으로만 드나든다.
  - 핵심 도로망과 이어지지 않는 조각은 버린다.
"""
import math

import osm_shapes as osm

MINOR_TYPES = {"residential": (20, 1), "living_street": (20, 1), "unclassified": (30, 1), "tertiary": (40, 2)}
ATTACH_NODE = 25.0    # 이 거리 안에 핵심 노드가 있으면 거기에 붙인다 (m)
ATTACH_EDGE = 22.0    # 이 거리 안에 핵심 도로가 있으면 그 도로를 나눠 붙인다 (m)


def inside(poly, p):
    x, y, c = p[0], p[1], False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def _split_poly(pts, s):
    L = osm.poly_len(pts)
    return osm.sub(pts, 0, s), osm.sub(pts, s, L)


def add_minor_roads(nodes, edges, area, skip_names, no_attach_nodes, no_split_edges, kmh=None, divided=()):
    """nodes·edges(build_schematic 형식)를 고쳐 골목을 더한다. 나뉜 핵심 엣지는 {원래 id: [조각 id, ...]}로 돌려준다."""
    pos, ways, _ = osm._load()
    kmh = kmh or (lambda v: round(v / 3.6, 2))
    xy = lambda n: (nodes[n][0], nodes[n][1])

    # 1) 골목 후보 OSM 길 (범위 안, 다리·지하·이름이 핵심 도로인 것 제외)
    minor, major_refs = [], set()
    for tags, refs in ways:
        hw = tags.get("highway")
        bad = tags.get("bridge") or tags.get("tunnel") or tags.get("layer", "0") != "0"
        if hw in MINOR_TYPES and not bad and tags.get("name") not in skip_names:
            minor.append((tags, refs))
        elif hw not in ("footway", "steps", "path", "pedestrian", "cycleway", "service", "track", "corridor"):
            major_refs.update(refs)
    use = {}
    for _, refs in minor:
        for r in refs:
            use[r] = use.get(r, 0) + 1
    split_at = {r for r, n in use.items() if n > 1} | major_refs

    # 2) 교차점마다 나눈 조각 (범위 밖 점에서 끊김)
    segs = []
    for tags, refs in minor:
        cur = []
        for r in refs:
            if not inside(area, pos[r]):
                if len(cur) > 1:
                    segs.append((tags, cur))
                cur = []
                continue
            cur.append(r)
            if r in split_at and len(cur) > 1:
                segs.append((tags, cur))
                cur = [r]
        if len(cur) > 1:
            segs.append((tags, cur))

    # 3) 핵심 도로 붙이기
    core = [e for e in edges if e[0] not in no_split_edges]
    pieces = {e[0]: [list(e)] for e in core}          # 원래 id → 조각 [id, from, to, lanes, speed, prio, shape, name]
    poly_of = lambda e: [p[:2] for p in e[6]] if e[6] else [xy(e[1]), xy(e[2])]
    rev_of = {}
    for e in core:
        if e[0] in divided:
            continue
        for f in core:
            if (f[1], f[2]) == (e[2], e[1]) and (e[6] is None) == (f[6] is None) and \
                    (e[6] is None or [p[:2] for p in f[6]] == [p[:2] for p in reversed(e[6])]):
                rev_of[e[0]] = f[0]                    # 같은 선을 반대로 달리는 짝 (둘 다 나눈다)
    attach_nodes = {n: xy(n) for n in nodes if n not in no_attach_nodes}
    mapped, counter = {}, [0]

    def split_piece(orig, p):
        best = None
        for k, pc in enumerate(pieces[orig]):
            pts = poly_of(pc)
            s = osm.project(pts, p)
            q = osm.point_at(pts, s)
            d = math.dist(p, q)
            if best is None or d < best[0]:
                best = (d, k, s, q, pts)
        return best

    def attach(r):
        if r in mapped:
            return mapped[r]
        p = pos[r]
        n, d = min(((n, math.dist(p, q)) for n, q in attach_nodes.items()), key=lambda t: t[1])
        if d <= ATTACH_NODE:
            mapped[r] = n
            return n
        best = None
        for orig in pieces:
            b = split_piece(orig, p)
            if orig in divided:                        # 중앙분리대 도로: 골목이 오른쪽에 있는 방향에만
                (ax, ay), (bx, by) = osm.point_at(b[4], b[2] - 1), osm.point_at(b[4], b[2] + 1)
                if (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) > 0:
                    continue
            if best is None or b[0] < best[0]:
                best = (*b, orig)
        if best is None or best[0] > ATTACH_EDGE:
            return None
        d, k, s, q, pts, orig = best
        L = osm.poly_len(pts)
        if s < 8 or s > L - 8:                         # 너무 끝이면 그 끝 노드에 붙인다
            pc = pieces[orig][k]
            n = pc[1] if s < 8 else pc[2]
            mapped[r] = n
            return n
        counter[0] += 1
        n = f"x{counter[0]}"
        nodes[n] = q
        attach_nodes[n] = q
        for o, pt in ((orig, q), (rev_of.get(orig), q)):
            if not o or o not in pieces:
                continue
            _, kk, ss, _, ptsk = split_piece(o, pt)
            pc = pieces[o][kk]
            a, b = _split_poly(ptsk, ss)
            a[-1] = b[0] = q
            pieces[o][kk:kk + 1] = [[pc[0], pc[1], n, *pc[3:6], a, pc[7]], [pc[0], n, pc[2], *pc[3:6], b, pc[7]]]
        mapped[r] = n
        return n

    new_edges, seen = [], set()
    for i, (tags, refs) in enumerate(segs):
        ends = []
        for r in (refs[0], refs[-1]):
            n = attach(r) if r in major_refs or any(math.dist(pos[r], xy(m)) < ATTACH_NODE for m in attach_nodes) \
                else None
            if n is None:
                n = f"o{r}"
                nodes.setdefault(n, pos[r])
            ends.append(n)
        a, b = ends
        if a == b or (a, b) in seen or (b, a) in seen:
            continue
        seen.add((a, b))
        pts = osm._rdp([pos[r] for r in refs], osm.SIMPLIFY)
        pts = [xy(a)] + pts[1:-1] + [xy(b)]
        spd, prio = MINOR_TYPES[tags["highway"]]
        name = tags.get("name", "골목")
        ow = tags.get("oneway")
        if ow == "-1":
            a, b, pts = b, a, list(reversed(pts))
        new_edges.append([f"m{i}", a, b, 1, kmh(spd), prio, pts, name])
        if ow not in ("yes", "-1", "1"):
            new_edges.append([f"m{i}r", b, a, 1, kmh(spd), prio, list(reversed(pts)), name])

    # 4) 핵심 엣지를 조각으로 바꾸기 (안 나뉜 것은 이름 그대로)
    split_map, out = {}, []
    for e in edges:
        if e[0] in pieces and len(pieces[e[0]]) > 1:
            ids = [f"{e[0]}#{k}" for k in range(len(pieces[e[0]]))]
            split_map[e[0]] = ids
            for pid, pc in zip(ids, pieces[e[0]]):
                out.append((pid, pc[1], pc[2], *pc[3:6], pc[6], pc[7]))
        else:
            out.append(e)

    # 5) 핵심 도로망과 이어진 골목만 남김
    adj = {}
    for e in out + [tuple(x) for x in new_edges]:
        adj.setdefault(e[1], set()).add(e[2])
        adj.setdefault(e[2], set()).add(e[1])
    start = next(iter(n for n in nodes if not n.startswith(("o", "x")) and n in adj))
    reach, stack = {start}, [start]
    while stack:
        for m in adj[stack.pop()]:
            if m not in reach:
                reach.add(m)
                stack.append(m)
    kept = [tuple(x) for x in new_edges if x[1] in reach and x[2] in reach]
    for n in [n for n in nodes if n.startswith("o") and n not in reach]:
        del nodes[n]
    edges[:] = out + kept
    return split_map, len(kept)
