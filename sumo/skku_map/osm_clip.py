"""OSM 원본에서 구현 범위(AREA) 안의 차도만 잘라 netconvert 입력을 만든다.

- 차도: secondary·tertiary·unclassified·residential·living_street (+ 각 link) + service(교내 도로·주차장 통로·단지 도로).
  네이버 로드뷰 선이 있는 길 기준. 집 앞 진입로(driveway)·드라이브스루·비상 통로만 뺀다.
- 범위 밖으로 나가는 길은 범위 경계에서 끊는다.
- 차로 수: OSM lanes 태그가 있으면 그대로, 없으면 아래 LANES 규칙 (지도·로드뷰로 확인한 값과 기존 모델 값).
- 버스 정류장 노드와 버스 노선(relation)은 같이 남겨 둔다 (netconvert --ptstop-output / --ptline-output).
"""
import math
import xml.etree.ElementTree as ET

LAT0, LON0 = 37.30055, 126.97268          # 원점 = 성대역 사거리
SKIP_SERVICE = {"driveway", "drive-through", "emergency_access"}
DRIVE = {"secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified",
         "residential", "living_street"}


def xy(lat, lon):
    return ((lon - LON0) * math.cos(math.radians(LAT0)) * 111320, (lat - LAT0) * 110574)


def lonlat(x, y):
    return LAT0 + y / 110574, LON0 + x / (math.cos(math.radians(LAT0)) * 111320)


def cross(poly, p, q):
    """선분 p→q가 범위 경계와 만나는 첫 점."""
    best = None
    for a, b in zip(poly, poly[1:] + poly[:1]):
        d = (q[0] - p[0]) * (b[1] - a[1]) - (q[1] - p[1]) * (b[0] - a[0])
        if abs(d) < 1e-9:
            continue
        t = ((a[0] - p[0]) * (b[1] - a[1]) - (a[1] - p[1]) * (b[0] - a[0])) / d
        u = ((a[0] - p[0]) * (q[1] - p[1]) - (a[1] - p[1]) * (q[0] - p[0])) / d
        if 0 <= t <= 1 and 0 <= u <= 1 and (best is None or t < best):
            best = t
    return (p[0] + (q[0] - p[0]) * best, p[1] + (q[1] - p[1]) * best) if best is not None else None


def inside(poly, p):
    x, y, c = p[0], p[1], False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


# 카카오 위성사진(스카이뷰)으로 센 차로 수 (2026-11-02, WORKLOG.md "차로 조사"). 잘린 길 id → 일방: n / 양방향: (정방향, 역방향)
LANES_VERIFIED = {
    "383158340": 3, "5552317800": 2, "7754668950": 2,          # 덕영대로 사거리 동쪽 (동행 본선 / 서행 본선 / 서행 연결로)
    "5899587190": (2, 2), "7755484360": (2, 2),                # 화산로 율전삼거리 서·동쪽
    "383167710": 3, "5612296390": 3, "5612296410": (3, 3),     # 일월로 (분리 구간 두 줄 + 서부로 쪽 양방향)
    "1024410150": 3, "7754717130": 3, "4720563970": 3, "7754717140": 3,   # 정자천로 (나무 심은 분리대 있는 4~6차로)
}


def lanes_rule(tags, mid):
    """OSM에 차로 수가 없을 때 쓰는 값 (한 방향 기준). mid = 길 가운데 좌표."""
    name, hw = tags.get("name", ""), tags.get("highway", "")
    x, y = mid
    if name == "서부로" and hw in ("secondary", "tertiary"):
        if tags.get("bridge") == "viaduct":
            return 2                      # 서부로 고가 (밤밭고가도로)
        if y < -1100:
            return 2                      # 서부로×일월로 남쪽 (로드뷰 확인)
        return 3 if y > 0 or y < -800 else 2   # 사거리 북쪽 3 (로드뷰), 착지 이후 3 (로드뷰), 고가 하부 지상 2 (로드뷰)
    if name in ("덕영대로", "밤밭지하차도") and not hw.endswith("_link"):
        return 3 if x > 100 else 2
    return None


LANE_W = 3.2
MEDIAN = {"정자천로": 4.0}          # 나무 심은 분리대 (위성사진). 나머지는 연석·가드레일 정도 1 m


def tighten(osm, pos):
    """분리 도로(같은 층에 나란히 놓인 일방 두 줄)를 실제처럼 붙인다.
    OSM 선은 각 차로 묶음의 가운데라 차로 수가 맞아도 사이가 비어 보인다 → 두 줄 사이를 (두 차로 폭 합)/2 + 분리대로 맞춘다.
    서부로 고가 구간처럼 두 줄 사이가 28 m 넘게 떨어진 곳(고가 밑 주차장 자리)은 그대로 둔다."""
    ws = []
    for w in osm.findall("way"):
        t = {x.get("k"): x.get("v") for x in w.findall("tag")}
        if t.get("oneway") not in ("yes", "-1") or t.get("highway") not in DRIVE | {"secondary_link", "tertiary_link"}:
            continue
        refs = [x.get("ref") for x in w.findall("nd")]
        lanes = int(t["lanes"]) if t.get("lanes", "").isdigit() else 1
        ws.append((refs, lanes, t.get("layer", "0"), t.get("name", "")))   # layer는 clip에서 -1/0/1로 맞춰 둠
    # 고가·지하차도 선 (두 줄 사이에 이런 선이 지나가면 고가 밑처럼 실제로 넓은 곳이라 붙이지 않는다)
    up = []
    for w in osm.findall("way"):
        if any(x.get("k") == "layer" for x in w.findall("tag")):
            up.append([pos[x.get("ref")] for x in w.findall("nd")])

    def between(p, q):
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        half = math.dist(p, q) / 2
        for line in up:
            for a, b in zip(line, line[1:]):
                dx, dy = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dy * dy or 1
                t = max(0, min(1, ((m[0] - a[0]) * dx + (m[1] - a[1]) * dy) / L2))
                if math.dist(m, (a[0] + t * dx, a[1] + t * dy)) < half - 2:
                    return True
        return False

    shift = {}
    for i, (ra, la, ya, na) in enumerate(ws):
        for j, (rb, lb, yb, nb) in enumerate(ws):
            if i == j or ya != yb:
                continue
            pb = [pos[r] for r in rb]
            want = (la + lb) * LANE_W / 2 + max(MEDIAN.get(na, 1.0), MEDIAN.get(nb, 1.0))
            for k, r in enumerate(ra):
                if r in rb:
                    continue
                p = pos[r]
                best = None
                for a, b in zip(pb, pb[1:]):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    L2 = dx * dx + dy * dy
                    if L2 < 1:
                        continue
                    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2
                    if not 0 <= t <= 1:
                        continue
                    q = (a[0] + t * dx, a[1] + t * dy)
                    d = math.dist(p, q)
                    # 나란한지: 이 점에서의 a 방향과 b 선분 방향
                    o = pos[ra[k - 1]] if k else pos[ra[k + 1]]
                    ax, ay = (p[0] - o[0], p[1] - o[1]) if k else (o[0] - p[0], o[1] - p[1])
                    La = math.hypot(ax, ay)
                    if La < 1 or abs((ax * dx + ay * dy) / (La * math.sqrt(L2))) < 0.9:
                        continue
                    if best is None or d < best[0]:
                        best = (d, q)
                if best and want + 1 < best[0] < 28 and (ya != "0" or not between(p, best[1])):
                    d, q = best
                    move = (d - want) / 2
                    shift.setdefault(r, []).append(((q[0] - p[0]) / d * move, (q[1] - p[1]) / d * move))
    for r, v in shift.items():
        dx = sum(a for a, _ in v) / len(v)
        dy = sum(b for _, b in v) / len(v)
        pos[r] = (pos[r][0] + dx, pos[r][1] + dy)
    return shift


SMALL = {"residential", "service", "living_street", "unclassified"}


def residential_areas(ways, pos):
    """아파트 단지 (landuse=residential 이고 이름 있는 면)."""
    out = []
    for w in ways.values():
        t = {x.get("k"): x.get("v") for x in w.findall("tag")}
        refs = [r.get("ref") for r in w.findall("nd")]
        if t.get("landuse") == "residential" and t.get("name") and refs[0] == refs[-1] and all(r in pos for r in refs):
            out.append([pos[r] for r in refs[:-1]])
    return out


def campus_area(ways, pos):
    w = ways.get("70081328")     # 성균관대학교 자연과학캠퍼스
    return [pos[r.get("ref")] for r in w.findall("nd")][:-1] if w is not None else []


def prune(osm, pos, apts, campus):
    """사용자 기준 (2026-11-02): 로드뷰가 없는 길, 로드뷰가 있어도 아주 작은 길은 만들지 않는다.
      - 아파트 단지 안 service 도로 (단지 내부 통로는 로드뷰가 거의 없다)
      - 막다른 골목: 끝에서 첫 교차로까지 80 m 안 되는 작은 길 (사슬처럼 이어진 것도 끝에서부터 차례로)
    교내 도로·주차장 통로, 범위 경계에서 잘린 길은 남긴다."""
    def length(w):
        p = [pos[r.get("ref")] for r in w.findall("nd")]
        return sum(math.dist(a, b) for a, b in zip(p, p[1:]))

    def tag(w, k):
        return next((t.get("v") for t in w.findall("tag") if t.get("k") == k), None)

    removed = 0
    for w in list(osm.findall("way")):
        p = [pos[r.get("ref")] for r in w.findall("nd")]
        mid = p[len(p) // 2]
        if tag(w, "highway") == "service" and not (campus and inside(campus, mid)) and any(inside(a, mid) for a in apts):
            osm.remove(w)
            removed += 1
    while True:
        deg = {}
        for w in osm.findall("way"):
            refs = [r.get("ref") for r in w.findall("nd")]
            for r in set(refs):
                deg[r] = deg.get(r, 0) + 1
        cut = []
        for w in osm.findall("way"):
            refs = [r.get("ref") for r in w.findall("nd")]
            if tag(w, "highway") not in SMALL or refs[0] == refs[-1]:
                continue
            if any(int(r) >= 9_000_000_000_000 for r in (refs[0], refs[-1])):      # 범위 경계에서 잘린 길
                continue
            mid = pos[refs[len(refs) // 2]]
            if campus and inside(campus, mid):
                continue
            dead = [r for r in (refs[0], refs[-1]) if deg.get(r, 0) == 1]
            if dead and len(dead) < 2 and length(w) < 80:
                cut.append(w)
        if not cut:
            break
        for w in cut:
            osm.remove(w)
        removed += len(cut)
    return removed


def clip(osm_files, area, out, oneway=None):
    """oneway = {잘린 길 id: "yes" | "-1"}: 지도로 확인해 OSM과 다른 일방통행을 덮어쓴다."""
    oneway = oneway or {}
    nodes, ways, rels = {}, {}, {}
    for f in osm_files:
        root = ET.parse(f).getroot()
        for n in root.findall("node"):
            nodes[n.get("id")] = n
        for w in root.findall("way"):
            ways[w.get("id")] = w
        for r in root.findall("relation"):
            rels[r.get("id")] = r
    pos = {i: xy(float(n.get("lat")), float(n.get("lon"))) for i, n in nodes.items()}

    in_area = {i for i, p in pos.items() if inside(area, p)}
    extra = {}

    def boundary_node(a, b):
        key = tuple(sorted((a, b)))
        if key not in extra:
            p = cross(area, pos[a], pos[b]) if inside(area, pos[a]) else cross(area, pos[b], pos[a])
            nid = str(9_000_000_000_000 + len(extra))
            lat, lon = lonlat(*p)
            nodes[nid] = ET.Element("node", id=nid, lat=f"{lat:.7f}", lon=f"{lon:.7f}")
            pos[nid] = p
            extra[key] = nid
        return extra[key]
    osm = ET.Element("osm", version="0.6", generator="osm_clip.py")
    keep_nodes, pieces = set(), {}
    for wid, w in ways.items():
        tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
        if tags.get("highway") not in DRIVE and not (
                tags.get("highway") == "service" and tags.get("service") not in SKIP_SERVICE):
            continue
        refs = [r.get("ref") for r in w.findall("nd") if r.get("ref") in pos]
        runs, cur = [], []
        for prev, r in zip([None] + refs, refs):
            if inside(area, pos[r]):
                if not cur and prev is not None:            # 경계 밖에서 들어옴 → 경계 위에 점을 만들어 시작
                    cur.append(boundary_node(prev, r))
                cur.append(r)
            elif cur:                                       # 경계 밖으로 나감 → 경계 위 점에서 끝
                cur.append(boundary_node(cur[-1], r))
                runs.append(cur)
                cur = []
        if len(cur) > 1:
            runs.append(cur)
        for k, run in enumerate(runs):
            nid = str(int(wid) * 10 + k)          # 잘린 조각마다 새 id
            pieces.setdefault(wid, []).append(nid)
            e = ET.SubElement(osm, "way", id=nid)
            for r in run:
                ET.SubElement(e, "nd", ref=r)
                keep_nodes.add(r)
            lanes = tags.get("lanes")
            if nid in LANES_VERIFIED:
                v = LANES_VERIFIED[nid]
                if isinstance(v, tuple):
                    tags.update({"lanes": str(sum(v)), "lanes:forward": str(v[0]), "lanes:backward": str(v[1])})
                else:
                    tags["lanes"] = str(v)
            elif not (lanes and lanes.isdigit() and 1 <= int(lanes) <= 4):
                mid = pos[run[len(run) // 2]]
                rule = lanes_rule(tags, mid)
                if rule:
                    tags["lanes"] = str(rule)
                else:
                    tags.pop("lanes", None)
            if nid in oneway:
                tags["oneway"] = oneway[nid]
            # 층: 고가·다리 1, 지하차도 -1, 나머지 0 (OSM layer 값이 길마다 1·2·5로 제각각이라 맞춘다 → --osm.layer-elevation 높이)
            lay = int(tags["layer"]) if tags.get("layer", "").lstrip("-").isdigit() else 0
            lay = 1 if tags.get("bridge") or lay > 0 else -1 if tags.get("tunnel") or lay < 0 else 0
            if lay:
                tags["layer"] = str(lay)
            else:
                tags.pop("layer", None)
            for k2, v in tags.items():
                ET.SubElement(e, "tag", k=k2, v=v)
    pruned = prune(osm, pos, residential_areas(ways, pos), campus_area(ways, pos))
    keep_nodes = {r.get("ref") for w in osm.findall("way") for r in w.findall("nd")}
    print(f"작은 골목·단지 안 도로 {pruned}개 뺌")
    moved = tighten(osm, pos)
    for i in moved:
        lat, lon = lonlat(*pos[i])
        nodes[i].set("lat", f"{lat:.7f}")
        nodes[i].set("lon", f"{lon:.7f}")
    for i, n in nodes.items():
        tags = {t.get("k"): t.get("v") for t in n.findall("tag")}
        if i in keep_nodes or (tags.get("highway") == "bus_stop" and i in in_area):
            osm.insert(0, n)
    for rid, r in rels.items():
        tags = {t.get("k"): t.get("v") for t in r.findall("tag")}
        if tags.get("route") != "bus":
            continue
        rel = ET.SubElement(osm, "relation", id=rid)
        n_members = 0
        for m in r.findall("member"):
            if m.get("type") == "way" and m.get("ref") in pieces:
                for p in pieces[m.get("ref")]:
                    ET.SubElement(rel, "member", type="way", ref=p, role=m.get("role", ""))
                    n_members += 1
            elif m.get("type") == "node" and m.get("ref") in in_area:
                ET.SubElement(rel, "member", type="node", ref=m.get("ref"), role=m.get("role", ""))
        for k2, v in tags.items():
            ET.SubElement(rel, "tag", k=k2, v=v)
        if not n_members:
            osm.remove(rel)
    ET.ElementTree(osm).write(out, encoding="utf-8", xml_declaration=True)
    return len(pieces), sum(len(v) for v in pieces.values())
