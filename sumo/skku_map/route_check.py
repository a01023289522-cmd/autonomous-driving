"""카카오맵 길찾기와 SUMO 도로망을 같은 출발·도착점으로 비교한다.

입력: checks.json (make_checks.py: 각 길의 10%·90% 지점), kakao_routes.txt ("길id:정방향m:역방향m[:T]")
각 방향마다
  카카오: 경로 길이가 두 점 사이 길이의 1.4배+60m 이내면 '바로 감', 아니면 '돌아감'
  SUMO : 두 점을 카카오처럼 가장 가까운 도로에 붙이고, 그 지점의 길 진행 방향 차로끼리 최단 경로 길이로 같은 판정
둘이 다르면 출력한다. (지하차도·고가처럼 카카오가 다른 층 도로에 점을 붙이는 곳은 '판정 불가')
"""
import json
import xml.etree.ElementTree as ET
import math
import os
import sys

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo"), "tools"))
import sumolib  # noqa: E402
from sumolib import geomhelper  # noqa: E402

import osm_clip  # noqa: E402

checks = {c["id"]: c for c in json.load(open("checks.json", encoding="utf-8"))}
kakao = {}
for tok in open("kakao_routes.txt", encoding="utf-8").read().split():
    wid, f, b, *flag = tok.split(":")
    kakao[wid] = (int(f), int(b), bool(flag))
root = ET.parse("clip.osm.xml").getroot()
pos = {n.get("id"): osm_clip.xy(float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")}
ways = {w.get("id"): [pos[r.get("ref")] for r in w.findall("nd")] for w in root.findall("way")}
# 경로 좌표로 다시 확인한 판정 (kakao_verified.txt)이 있으면 그것을 쓴다
verified = {}
for ln in open("kakao_verified.txt", encoding="utf-8"):
    if ln.strip() and not ln.startswith("#"):
        wid, v, *_ = ln.split()
        verified[wid] = {"both": (True, True), "fwd": (True, False), "bwd": (False, True)}[v]
net = sumolib.net.readNet(sys.argv[1] if len(sys.argv) > 1 else "skku.net.xml")


def edge_at(p, d, r=25):
    """카카오처럼 p에서 가장 가까운 도로에 붙인 뒤, 그 도로에서 방향 d로 가는 엣지와 위치.
    가장 가까운 도로(3 m, 교차로 안이면 8 m 이내 엣지와 그 반대 방향 엣지)에 d 방향이 없으면 '돌아가야 함'(False)."""
    near = [(e, dist) for e, dist in net.getNeighboringEdges(p[0], p[1], r) if e.allows("passenger")]
    if not near:
        return None
    d0 = min(dist for _, dist in near)
    road = {e for e, dist in near if dist <= max(d0 + 3, 8)}
    road |= {e for e, _ in near if any(e.getFromNode() == x.getToNode() and e.getToNode() == x.getFromNode()
                                       for x in road)}
    best = False
    for e, dist in near:
        if e not in road:
            continue
        sh = [q[:2] for q in e.getShape()]
        pos, _ = geomhelper.polygonOffsetAndDistanceToPoint(p, sh)
        # p 근처(꺾이는 꼭짓점이면 앞뒤 구간 모두)에서 d 방향으로 가는 구간이 있는가
        segs = [(geomhelper.distancePointToLine(p, a, b), a, b) for a, b in zip(sh, sh[1:]) if math.dist(a, b) > 0.1]
        md = min((s[0] for s in segs), default=0)
        ok = any(m <= md + 2 and ((b[0] - a[0]) * d[0] + (b[1] - a[1]) * d[1]) / math.dist(a, b) > 0.5
                 for m, a, b in segs)
        if ok and (not best or dist < best[2]):
            best = (e, pos * e.getLength() / max(geomhelper.polyLength(sh), 0.1), dist)
    return best


def tangent(line, p, sign):
    """OSM 길 line 위에서 p 지점의 진행 방향 (sign=-1이면 역방향)."""
    off, _ = geomhelper.polygonOffsetAndDistanceToPoint(p, line)
    acc = 0.0
    for a, b in zip(line, line[1:]):
        L = math.dist(a, b)
        if acc + L >= off - 1e-6 and L > 0.1:
            break
        acc += L
    return (sign * (b[0] - a[0]) / L, sign * (b[1] - a[1]) / L)


def sumo_len(a, b, line, sign):
    ea, eb = edge_at(a, tangent(line, a, sign)), edge_at(b, tangent(line, b, sign))
    if ea is None or eb is None:
        return None
    if ea is False or eb is False:
        return math.inf
    (e1, p1, _), (e2, p2, _) = ea, eb
    if e1 == e2 and p2 >= p1:
        return p2 - p1
    path, cost = net.getShortestPath(e1, e2) if e1 != e2 else (None, None)
    if e1 == e2:   # 같은 엣지에서 뒤로 가야 함: 한 바퀴 돌아오는 경로
        loops = [net.getShortestPath(o, e1) for o in e1.getOutgoing()]
        loops = [c + e1.getLength() for pth, c in loops if pth]
        return min(loops) - p1 + p2 if loops else math.inf
    return cost - p1 - (e2.getLength() - p2) if path else math.inf


ok, bad, unclear, divided, pruned = [], [], [], [], []
for wid, c in checks.items():
    if wid not in kakao:
        continue
    if wid not in ways:          # 작은 골목·단지 안 도로로 뺀 길 (osm_clip.prune)
        pruned.append(wid)
        continue
    kf, kb, timeout = kakao[wid]
    A, B = osm_clip.xy(*c["A"]), osm_clip.xy(*c["B"])
    direct = lambda m: m is not None and m <= 1.4 * c["len"] + 60
    sf, sb = sumo_len(A, B, ways[wid], 1), sumo_len(B, A, ways[wid], -1)
    k = verified.get(wid, (direct(kf), direct(kb)))
    s = (direct(sf) if sf is not None else None, direct(sb) if sb is not None else None)
    name = c["name"] or c["hw"]
    line = (f"{wid:>12} {name:<12} {c['len']:>4}m | 카카오 {kf:>5}/{kb:>5}m {'바로' if k[0] else '돌아'}/{'바로' if k[1] else '돌아'}"
            f" | SUMO {'-' if sf is None else 'inf' if sf == math.inf else round(sf):>5}/"
            f"{'-' if sb is None else 'inf' if sb == math.inf else round(sb):>5}m | OSM oneway={c['oneway']}")
    if timeout or not any(k):
        unclear.append(line)
    elif tuple(bool(x) for x in s) == k:
        ok.append(line + (" (경로 좌표로 확인)" if wid in verified else ""))
    elif c["oneway"] == "yes" and k[0] and s[0] and (s[1] is not True or not k[1]):
        divided.append(line)   # OSM 일방 그대로 맞음: 한쪽이 바로 옆 반대 방향 길(분리 도로·램프)에 붙은 것
    else:
        bad.append(line)
print(f"== 다름 ({len(bad)})\n" + "\n".join(bad))
print(f"== OSM 일방통행 그대로 (역방향 점이 옆 반대 방향 길에 붙은 것) ({len(divided)})\n" + "\n".join(divided))
print(f"== 판정 불가 ({len(unclear)})\n" + "\n".join(unclear))
print(f"== 같음 ({len(ok)})")
print(f"== 뺀 길 ({len(pruned)})")
