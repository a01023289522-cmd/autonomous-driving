"""주차장: 통로 양옆 한 칸 한 칸 주차면(<space>)과, 그 주차장에 들렀다 가는 차.

- 고가 밑 공영주차장(P1~P3)과 교내·역 주변 OSM 주차장(amenity=parking 면 안의 통로 엣지).
- 주차면: 통로 차로 가운데에서 1.6 + 2.5 m 떨어진 곳에 2.5 m 간격, 통로와 직각으로 나란히 (userdoc/Simulation/ParkingArea.html).
  다른 도로와 겹치는 칸은 뺀다.
- SUMO는 한 주차 구역 안에서 빈칸을 앞에서부터 채운다 → 구역을 6칸씩 잘게 나누고 차마다 구역을 무작위로 골라
  주차가 흩어지게 한다.
"""
import math
import random
import xml.etree.ElementTree as ET

from sumolib import geomhelper

import osm_clip

PITCH, DEPTH, CHUNK = 2.5, 5.0, 6


def lot_polygons(osm_files, area):
    polys = []
    for f in osm_files:
        root = ET.parse(f).getroot()
        pos = {n.get("id"): osm_clip.xy(float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")}
        for w in root.findall("way"):
            t = {x.get("k"): x.get("v") for x in w.findall("tag")}
            refs = [r.get("ref") for r in w.findall("nd")]
            if t.get("amenity") == "parking" and refs[0] == refs[-1] and all(r in pos for r in refs):
                p = [pos[r] for r in refs[:-1]]
                if osm_clip.inside(area, (sum(x for x, _ in p) / len(p), sum(y for _, y in p) / len(p))):
                    polys.append(p)
    return polys


def height(edge):
    return edge.getLanes()[0].getShape3D()[0][2]


def spaces_along(net, edge, sides):
    """엣지 첫 차로를 따라 주차면 (거리, x, y, 각도). sides: 1 = 오른쪽, -1 = 왼쪽."""
    lane = edge.getLanes()[0]
    sh = [p[:2] for p in lane.getShape()]
    L = geomhelper.polyLength(sh)
    off = lane.getWidth() / 2 + DEPTH / 2
    out, d = [], 6 + PITCH / 2
    others = {edge.getID()} | {e.getID() for e in edge.getToNode().getOutgoing() if e.getToNode() == edge.getFromNode()}
    while d < L - 6:
        cx, cy = geomhelper.positionAtShapeOffset(sh, d)
        ax, ay = geomhelper.positionAtShapeOffset(sh, max(d - 1, 0))
        bx, by = geomhelper.positionAtShapeOffset(sh, min(d + 1, L))
        n = math.hypot(bx - ax, by - ay) or 1
        ux, uy = (bx - ax) / n, (by - ay) / n
        # <space angle>: sumo-gui는 주차면의 긴 변을 (angle + 90)도(수학 각도, 동쪽 0·반시계) 방향으로 그린다 (화면으로 확인).
        #   통로와 직각인 칸 = angle을 통로 방향의 수학 각도로. 오른쪽·왼쪽 칸은 180도 차이 (차 머리가 칸 안쪽을 향하게)
        ang = math.degrees(math.atan2(uy, ux))
        for s in sides:
            x, y = cx + uy * off * s, cy - ux * off * s
            if not any(e.getID() not in others and dist < 3.5 and abs(height(e)) < 3      # 고가 밑은 겹쳐도 된다
                       for e, dist in net.getNeighboringEdges(x, y, 4)):
                out.append((d, x, y, (ang + (0 if s > 0 else 180)) % 360))
        d += PITCH
    return out


def areas_for_edge(net, edge, sides, prefix, name):
    """주차면을 CHUNK칸씩 묶어 parkingArea 여러 개로."""
    sp = spaces_along(net, edge, sides)
    rows, ids = [], []
    for k in range(0, len(sp), CHUNK * len(sides)):
        part = sp[k:k + CHUNK * len(sides)]
        if not part:
            continue
        aid = f"{prefix}_{len(ids)}"
        a, b = max(part[0][0] - PITCH, 0.5), min(part[-1][0] + PITCH, edge.getLength() - 0.5)
        rows.append(f'    <parkingArea id="{aid}" lane="{edge.getLanes()[0].getID()}" startPos="{a:.1f}" endPos="{b:.1f}" '
                    f'roadsideCapacity="0" name="{name}" friendlyPos="true">\n'
                    + "".join(f'        <space x="{x:.2f}" y="{y:.2f}" width="2.4" length="{DEPTH}" angle="{ang:.1f}"/>\n'
                              for _, x, y, ang in part)
                    + "    </parkingArea>\n")
        ids.append(aid)
    return rows, ids


def build(net, osm_files, area, campus_poly):
    """반환: (additional 줄들, {주차장 이름: [parkingArea id...]})."""
    rows, groups = [], {}
    # 고가 밑 공영주차장: 통로 엣지 P1_aisle ~ P3_aisle, 양쪽 주차
    for lot in ("P1", "P2", "P3"):
        if net.hasEdge(f"{lot}_aisle"):
            r, ids = areas_for_edge(net, net.getEdge(f"{lot}_aisle"), (1, -1), lot, f"공영주차장{lot[1]}")
            rows += r
            if ids:
                groups[lot] = ids
    # OSM 주차장 면 안의 통로들
    for i, poly in enumerate(lot_polygons(osm_files, area)):
        cx, cy = sum(x for x, _ in poly) / len(poly), sum(y for _, y in poly) / len(poly)
        name = "교내 주차장" if campus_poly and osm_clip.inside(campus_poly, (cx, cy)) else "주차장"
        ids = []
        for e in net.getEdges():
            sh = e.getShape()
            if (not e.allows("passenger") or e.getID().startswith(("hw_", "P1_", "P2_", "P3_"))
                    or not e.getType().endswith("service") or abs(height(e)) > 3):      # 주차 통로만 (다리·큰길 제외)
                continue
            mid = sh[len(sh) // 2][:2]
            if not osm_clip.inside(poly, mid) or e.getLength() < 15:
                continue
            two_way = any(o.getToNode() == e.getFromNode() for o in e.getToNode().getOutgoing())
            r, got = areas_for_edge(net, e, (1,) if two_way else (1, -1), f"L{i}_{e.getID().replace('#', '_')}", name)
            rows += r
            ids += got
        if ids:
            groups[f"L{i}"] = ids
    return rows, groups


def vehicles(groups, ends, per_hour, seed=7):
    """주차하러 오는 차: 경계 큰길에서 와서 무작위 구역에 세웠다가 다른 경계로 나간다.
    고가 밑 공영주차장은 잠깐(5~20분), 교내·역 주변 주차장은 길게(20~60분)."""
    rnd = random.Random(seed)
    srcs = [v[0] for v in ends.values()]
    snks = [v[1] for v in ends.values()]
    out = []
    for lot, ids in groups.items():
        n = per_hour.get(lot[:2] if lot.startswith("P") else "L", 0)
        n = round(n * (len(ids) / 10 if not lot.startswith("P") else 1))
        dur = (300, 1200) if lot.startswith("P") else (1200, 3600)
        for k in range(n):
            t = rnd.uniform(0, 3600)
            out.append((t, f'    <trip id="park_{lot}_{k}" type="parker" depart="{t:.1f}" from="{rnd.choice(srcs)}" '
                           f'to="{rnd.choice(snks)}" departLane="best">'
                           f'<stop parkingArea="{rnd.choice(ids)}" duration="{rnd.randint(*dur)}"/></trip>\n'))
    return [r for _, r in sorted(out)]
