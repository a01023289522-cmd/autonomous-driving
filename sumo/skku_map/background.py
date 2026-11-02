"""배경: OSM 건물·아파트 단지·공원·물·철도를 옅은 색 면으로, 큰 지명(아파트 단지·학교·역·캠퍼스 큰 건물)을 글자로 (영어, NAMES).

도로가 주인공이라 배경은 지도처럼 간결하게: 채도 낮은 색, 도로보다 아래 층(layer 음수).
SUMO 폴리곤·POI (userdoc/Simulation/Shapes.html). POI 글자는 type 값으로 보인다 (skku.gui.xml poiType_show).
"""
import math
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

import osm_clip

# (OSM 키, 값 또는 None=아무 값) → (색, layer)
STYLE = [
    (("landuse", "residential"), ("231,228,221", -20)),
    (("amenity", "university"), ("234,231,240", -19)),
    (("amenity", "school"), ("234,231,240", -19)),
    (("amenity", "parking"), ("226,226,230", -18)),
    (("landuse", "grass"), ("214,229,204", -17)),
    (("leisure", "park"), ("214,229,204", -17)),
    (("leisure", "garden"), ("214,229,204", -17)),
    (("landuse", "forest"), ("202,222,195", -17)),
    (("natural", "wood"), ("202,222,195", -17)),
    (("natural", "grassland"), ("214,229,204", -17)),
    (("leisure", "pitch"), ("200,224,196", -16)),
    (("natural", "water"), ("196,220,236", -15)),
    (("building", None), ("214,210,202", -10)),
]
RAIL_COLOR = "184,184,190"

# sumo-gui 글꼴에는 한글이 없어(네모로 깨짐) 지명은 영어로. 큰 곳은 직접 옮기고, 나머지는 로마자(국어의 로마자 표기법 기본 규칙)
NAMES = {
    "성균관대": "SKKU Station (Line 1)", "성균관대학교 자연과학캠퍼스": "SKKU Natural Sciences Campus",
    "성균관대역 환승주차장": "SKKU Stn. Park & Ride", "롯데마트": "Lotte Mart", "이슈나인": "Issue Nine",
    "한국지역난방공사 수원열원점": "KDHC Suwon Plant", "베스트 타운": "Best Town", "삼전연립": "Samjeon Villa",
    "주공뜨란채": "Jugong Tteuranchae Apt.", "일월 그린하우스": "Ilwol Greenhouse",
    "학생회관": "Student Center", "제1공학관": "Engineering Bldg 1", "제2공학관": "Engineering Bldg 2",
    "제2과학관": "Science Bldg 2", "기초학문관": "Basic Sciences Bldg", "의학관": "Medical Bldg",
    "체육관": "Gym", "대강당": "Auditorium", "수성관": "Suseong Hall", "산학협력관": "Industry Collaboration Bldg",
    "제2종합연구동": "Research Bldg 2", "제약기술관": "Pharmacy Bldg", "글로벌 광장": "Global Plaza",
    "N 센터": "N Center", "모듈러동": "Modular Bldg", "유틸리티센터": "Utility Center",
    "E센터 및 CNS센터": "E Center / CNS Center", "기숙사 의관": "Dorm (Uigwan)", "기숙사 신관 B동": "Dorm (Singwan B)",
    "웅비관": "Woongbi Hall",
    "천천 삼성 래미안 아파트": "Cheoncheon Raemian Apt.", "천천동 푸르지오 아파트": "Cheoncheon Prugio Apt.",
    "삼성1단지 아파트": "Samsung Apt. Complex 1", "삼성2단지 아파트": "Samsung Apt. Complex 2",
    "한라비발디 아파트": "Halla Vivaldi Apt.", "현대 아파트": "Hyundai Apt.", "수원일성 아파트": "Suwon Ilsung Apt.",
    "한일신안아파트": "Hanil Sinan Apt.", "율전이안아파트": "Yuljeon Ian Apt.", "삼호진덕 아파트": "Samho Jindeok Apt.",
    "경기체육고등학교": "Gyeonggi Sports High School", "경기체육 고등학교": "Gyeonggi Sports High School",
}
SUFFIX = [("초등학교", "Elem. School"), ("중학교", "Middle School"), ("고등학교", "High School"),
          ("아파트", "Apt."), ("어린이공원", "Children's Park"), ("공원", "Park")]
_INI = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
_VOW = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu",
        "eu", "ui", "i"]
_FIN = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t", "ng",
        "t", "t", "k", "t", "p", "t"]


def romanize(word):
    out = []
    for ch in word:
        c = ord(ch) - 0xAC00
        if not 0 <= c < 11172:
            out.append(ch)
            continue
        out.append(_INI[c // 588] + _VOW[c % 588 // 28] + _FIN[c % 28])
    s = "".join(out)
    return s[:1].upper() + s[1:]


def english(name):
    name = name.strip()
    if name in NAMES:
        return NAMES[name]
    tail = ""
    for ko, en in SUFFIX:
        if name.endswith(ko):
            name, tail = name[:-len(ko)], " " + en
            break
    return " ".join(romanize(w) for w in name.split()) + tail


def area(pts):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2


def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def write(osm_files, area_poly, out, margin=60):
    big = [(x * 1.0, y * 1.0) for x, y in area_poly]
    cx, cy = centroid(big)
    big = [(cx + (x - cx) * 1.08, cy + (y - cy) * 1.08) for x, y in big]     # 범위보다 조금 넓게
    nodes, ways, labels = {}, [], []
    for f in osm_files:
        root = ET.parse(f).getroot()
        for n in root.findall("node"):
            p = osm_clip.xy(float(n.get("lat")), float(n.get("lon")))
            nodes[n.get("id")] = p
            t = {x.get("k"): x.get("v") for x in n.findall("tag")}
            if t.get("railway") == "station" and t.get("name") and osm_clip.inside(big, p):
                labels.append((t["name"], p, 3))
        ways += root.findall("way")
    rows, seen = [], set()
    for w in ways:
        if w.get("id") in seen:
            continue
        seen.add(w.get("id"))
        t = {x.get("k"): x.get("v") for x in w.findall("tag")}
        pts = [nodes[r.get("ref")] for r in w.findall("nd") if r.get("ref") in nodes]
        if len(pts) < 2:
            continue
        if t.get("railway") == "rail" and not t.get("service"):
            pts = [p for p in pts if osm_clip.inside(big, p)]
            if len(pts) > 1:
                rows.append(f'    <poly id="bg_rail_{w.get("id")}" type="1호선" color="{RAIL_COLOR}" fill="0" lineWidth="7" '
                            f'layer="-8" shape="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}"/>\n')
            continue
        if t.get("waterway") == "stream":
            pts = [p for p in pts if osm_clip.inside(big, p)]
            if len(pts) > 1:
                rows.append(f'    <poly id="bg_w_{w.get("id")}" type="하천" color="196,220,236" fill="0" lineWidth="4" '
                            f'layer="-15" shape="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}"/>\n')
            continue
        style = next((s for (k, v), s in STYLE if k in t and (v is None or t[k] == v)), None)
        if not style or pts[0] != pts[-1] or len(pts) < 4:
            continue
        c = centroid(pts[:-1])
        if not osm_clip.inside(big, c):
            continue
        color, layer = style
        a = area(pts[:-1])
        rows.append(f'    <poly id="bg_{w.get("id")}" type="배경" color="{color}" fill="1" layer="{layer}" '
                    f'shape="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}"/>\n')
        name = t.get("name")
        if name and (t.get("landuse") == "residential" or t.get("amenity") in ("school", "university")
                     or t.get("leisure") == "park" and a > 3000 or "building" in t and a > 1500):
            labels.append((name, c, 2 if t.get("landuse") == "residential" or t.get("amenity") else 1))
    # 글자: 큰 것부터, 가까운 글자끼리 겹치지 않게 (60 m 안에 이미 있으면 뺀다)
    placed = []
    for name, p, rank in sorted(labels, key=lambda l: -l[2]):
        if any(math.dist(p, q) < 60 or english(n) == english(name) for n, q in placed):
            continue
        placed.append((name, p))
    for i, (name, (x, y)) in enumerate(placed):
        rows.append(f'    <poi id="bg_lbl_{i}" type={quoteattr(english(name))} x="{x:.1f}" y="{y:.1f}" color="0,0,0,0" layer="-1"/>\n')
    with open(out, "w", encoding="utf-8") as f:
        f.write("<additional>\n" + "".join(rows) + "</additional>\n")
    return len(rows) - len(placed), len(placed)
