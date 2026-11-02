"""카카오맵 길찾기로 확인할 구간 목록: 잘라낸 OSM의 각 길마다 10%·90% 지점 (양방향)."""
import json
import math
import xml.etree.ElementTree as ET

import osm_clip

root = ET.parse("clip.osm.xml").getroot()
pos = {n.get("id"): (float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")}
checks = []
for w in root.findall("way"):
    tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
    pts = [pos[r.get("ref")] for r in w.findall("nd")]
    xy = [osm_clip.xy(*p) for p in pts]
    seg = [math.dist(a, b) for a, b in zip(xy, xy[1:])]
    L = sum(seg)
    if L < 50:
        continue

    def at(f):
        s, acc = f * L, 0.0
        for (p, q), d in zip(zip(pts, pts[1:]), seg):
            if acc + d >= s:
                t = (s - acc) / d
                return round(p[0] + (q[0] - p[0]) * t, 6), round(p[1] + (q[1] - p[1]) * t, 6)
            acc += d
        return pts[-1]
    a, b = at(0.1), at(0.9)
    checks.append({"id": w.get("id"), "name": tags.get("name", ""), "hw": tags.get("highway"),
                   "oneway": tags.get("oneway", "no"), "len": round(0.8 * L), "A": a, "B": b})
json.dump(checks, open("checks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(checks), "ways; total routes", 2 * len(checks))
