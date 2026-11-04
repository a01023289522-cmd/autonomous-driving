"""실제 버스 노선(bus_kakao.json, 카카오맵 노선 경로·정류장)을 SUMO 도로망에 맞춰 버스 정류장과 운행을 만든다.

노선 경로(50 m 간격 좌표)를 도로에 붙이고(진행 방향이 맞는 가장 가까운 엣지), 이어지는 엣지 사이는 최단 경로로 잇는다.
정류장은 그 노선이 지나는 엣지 위 가장 가까운 곳에 놓는다 (같은 이름·같은 엣지면 노선끼리 함께 쓴다).
배차 간격은 카카오 표기("10~15분")의 가운데 값.
"""
import json
import math
import os
import re
import sys

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo"), "tools"))
import sumolib  # noqa: E402
from sumolib import geomhelper  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build import AREA  # noqa: E402


def inside(p, poly=AREA):
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < x1 + (p[1] - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def pieces(run):
    """범위 안에 든 연속 구간들 (경계 바깥 점은 버린다)."""
    out, cur = [], []
    for p in run:
        if inside(p) and geomhelper.distancePointToPolygon(p, AREA + AREA[:1]) > 15:
            cur.append(p)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [c for c in out if len(c) >= 3]


def pts(s):
    return [tuple(map(float, p.split())) for p in s.split(",")]


def elevated(e):
    """서부로 고가(via_sb, via_nb). 버스는 이 고가를 타지 않는다: 지상 서부로를 고가에서 띄워 그려서(viaduct.py) 카카오 노선
    좌표가 고가에 더 가까워, 지상 정류장(성균관대역·성균관대학교·삼성아파트)이 고가 위에 놓였었다.
    (덕영대로 율전고가교도 +6 m지만 버스가 실제로 다니는 길이라 빼지 않는다)"""
    return e.getID().startswith("via_")


def heading_at(sh, off):
    """꺾은선 sh의 offset 지점 진행 방향 (단위 벡터)."""
    acc = 0.0
    for a, b in zip(sh, sh[1:]):
        L = math.dist(a, b)
        if acc + L >= off or (a, b) == (sh[-2], sh[-1]):
            break
        acc += L
    return (b[0] - a[0]) / max(L, 1e-6), (b[1] - a[1]) / max(L, 1e-6)


def opposite_side(net, p, e, dist):
    """정류장 좌표 p가 이 버스가 달리는 엣지 e보다 반대 방향 도로에 더 가까우면 True (길 건너편 정류장).
    왼쪽·오른쪽으로 가르지 않는 이유: 지상 서부로는 고가에서 띄워 그려서 실제 남행 정류장이 도로 왼쪽에 놓인다."""
    d = heading_at([q[:2] for q in e.getShape()], geomhelper.polygonOffsetAndDistanceToPoint(p, [q[:2] for q in e.getShape()])[0])
    for o, od in net.getNeighboringEdges(p[0], p[1], dist + 1):
        if o == e or not o.allows("bus") or elevated(o) or od >= dist:
            continue
        osh = [q[:2] for q in o.getShape()]
        h = heading_at(osh, geomhelper.polygonOffsetAndDistanceToPoint(p, osh)[0])
        if h[0] * d[0] + h[1] * d[1] < -0.5:
            return True
    return False


def candidates(net, p, d, r=25, k=4):
    """p 근처에서 방향 d로 가는 버스 통행 가능 엣지 후보 (가까운 순 k개): (엣지, 거리, 엣지 위 위치)."""
    out = []
    for e, dist in net.getNeighboringEdges(p[0], p[1], r):
        if not e.allows("bus") or elevated(e):
            continue
        sh = [q[:2] for q in e.getShape()]
        off, _ = geomhelper.polygonOffsetAndDistanceToPoint(p, sh)
        acc = 0.0
        for a, b in zip(sh, sh[1:]):
            L = math.dist(a, b)
            if acc + L >= off - 1e-6 and L > 0.1:
                break
            acc += L
        if L > 0.1 and ((b[0] - a[0]) * d[0] + (b[1] - a[1]) * d[1]) / L > 0.5:
            out.append((e, dist, off * e.getLength() / max(geomhelper.polyLength(sh), 0.1)))
    return sorted(out, key=lambda c: c[1])[:k]


def match(net, run):
    """좌표열 → 이어진 엣지열들 (은닉 마르코프 지도 맞춤: 가까움 + 도로를 따라간 거리가 점 사이 거리와 비슷할수록 좋음).
    고가·지하차도처럼 위아래로 겹친 길을 점마다 따로 고르지 않고 경로 전체로 고른다. 이어지지 않으면 끊는다."""
    sp = {}

    def route_len(a, b, straight):
        (ea, _, pa), (eb, _, pb) = a, b
        if ea == eb:
            return pb - pa if pb >= pa - 5 else None
        key = (ea.getID(), eb.getID())
        if key not in sp:
            path, cost = net.getShortestPath(ea, eb, vClass="bus", maxCost=3 * straight + 400)
            sp[key] = (path, cost) if path else (None, None)
        path, cost = sp[key]
        return None if path is None else cost - pa - (eb.getLength() - pb)

    pts_ = []
    for i, p in enumerate(run):
        q, o = run[min(i + 1, len(run) - 1)], run[max(i - 1, 0)]
        d = (q[0] - o[0], q[1] - o[1])
        L = math.hypot(*d)
        if L >= 1:
            pts_.append((p, candidates(net, p, (d[0] / L, d[1] / L))))
    problems = [f"도로 없음 ({p[0]:.0f},{p[1]:.0f})" for p, c in pts_ if not c]
    pts_ = [(p, c) for p, c in pts_ if c]
    if not pts_:
        return [], problems
    BREAK = 40.0
    cost = [[(c[1] / 8) ** 2 / 2 for c in pts_[0][1]]]
    back = [[None] * len(pts_[0][1])]
    for i in range(1, len(pts_)):
        (p0, c0), (p1, c1) = pts_[i - 1], pts_[i]
        straight = math.dist(p0, p1)
        row, brow = [], []
        for b in c1:
            best = (min(cost[-1]) + BREAK, (None, True))       # 끊고 새로 시작
            for j, a in enumerate(c0):
                rl = route_len(a, b, straight)
                if rl is None or rl > 3 * straight + 300:
                    continue
                v = cost[-1][j] + abs(rl - straight) / 10
                if v < best[0]:
                    best = (v, (j, False))
            row.append(best[0] + (b[1] / 8) ** 2 / 2)
            brow.append(best[1])
        cost.append(row)
        back.append(brow)
    # 되짚기
    j = min(range(len(cost[-1])), key=lambda t: cost[-1][t])
    chosen = []
    for i in range(len(pts_) - 1, -1, -1):
        chosen.append((pts_[i][1][j], back[i][j][1] if i else True))
        if i:
            pj, brk = back[i][j]
            j = pj if pj is not None else min(range(len(cost[i - 1])), key=lambda t: cost[i - 1][t])
    chosen.reverse()
    segs, seq = [], []
    for i, (c, brk) in enumerate(chosen):
        e = c[0]
        if brk and seq:
            problems.append(f"끊김 ({pts_[i][0][0]:.0f},{pts_[i][0][1]:.0f}) {seq[-1].getID()} → {e.getID()}")
            segs.append(seq)
            seq = []
        if not seq:
            seq = [e]
        elif seq[-1] != e:
            path, _ = sp.get((seq[-1].getID(), e.getID()), (None, None))
            seq += list(path[1:]) if path else [e]
    segs.append(seq)
    return [s for s in segs if sum(e.getLength() for e in s) > 150], problems


def period(iv):
    nums = [int(x) for x in re.findall(r"\d+", iv)]
    return 60 * sum(nums) / len(nums) if nums else 900


def build(net_file, rou_out, stops_out, report=print):
    net = sumolib.net.readNet(net_file)
    data = json.load(open(os.path.join(HERE, "bus_kakao.json"), encoding="utf-8"))["lines"]
    byname = {l["n"]: l for l in data}
    stops = {}          # (이름, 엣지) → (id, 위치)
    rows = []
    for line in data:
        runs = line["r"]
        while isinstance(runs, str):           # "61" = 노선 61과 같은 경로
            runs = byname[runs]["r"]
        named = [(int(o), nm, tuple(map(float, xy.split()))) for o, nm, xy in (s.split(":") for s in line["st"])]
        k = -1
        for run in (pc for r in runs for pc in pieces(pts(r))):
          segs, problems = match(net, run)
          for pr in problems:
              report(f"  {line['n']}: {pr}")
          for edges in segs:
            k += 1
            on = {e.getID(): i for i, e in enumerate(edges)}
            # 이 구간 근처 정류장: 경로 엣지 위 25 m 안, 경로 순서대로
            seq = []
            for order, nm, p in named:
                if min(math.dist(p, q) for q in run) > 40:
                    continue
                cand = [(e, dd) for e, dd in net.getNeighboringEdges(p[0], p[1], 25) if e.getID() in on]
                if not cand:
                    continue
                e, de = min(cand, key=lambda c: c[1])
                if opposite_side(net, p, e, de):
                    continue                    # 길 건너편 = 반대 방향 정류장 (노선 정류장 목록에는 오가는 방향이 다 들어 있다)
                sh = [q[:2] for q in e.getShape()]
                pos = geomhelper.polygonOffsetAndDistanceToPoint(p, sh)[0]
                pos = min(max(pos * e.getLength() / max(geomhelper.polyLength(sh), 0.1), 15), e.getLength() - 1)
                key = (nm, e.getID())
                if key not in stops:
                    stops[key] = (f"bs_{len(stops)}", pos)
                seq.append((on[e.getID()], stops[key][1], stops[key][0]))
            seq.sort()
            start = [0.0]
            for e in edges:
                start.append(start[-1] + e.getLength())
            sids, last = [], -1e9
            for i, pos, sid in seq:
                # 이름만 다르고 거의 같은 자리인 정류장(예: 삼성아파트 / 삼성1차아파트)은 한 번만 선다
                if sid not in sids and start[i] + pos - last >= 30:
                    sids.append(sid)
                    last = start[i] + pos
            rid = f"bus_{line['n']}_{k}"
            rows.append(f'    <route id="r_{rid}" edges="{" ".join(e.getID() for e in edges)}">\n'
                        + "".join(f'        <stop busStop="{s}" duration="20"/>\n' for s in sids)
                        + "    </route>\n"
                        f'    <flow id="{rid}" type="bus" begin="0" end="3600" period="{period(line["iv"]):.0f}" '
                        f'route="r_{rid}" departLane="best"/>\n')
            report(f"  {line['n']:>5} 구간{k}: 엣지 {len(edges)}개, 정류장 {len(sids)}곳, {period(line['iv']) / 60:.0f}분 간격")
    with open(stops_out, "w", encoding="utf-8") as f:
        f.write("<additional>\n")
        for (nm, eid), (sid, pos) in sorted(stops.items(), key=lambda kv: kv[1][0]):
            e = net.getEdge(eid)
            lane = next((ln for ln in e.getLanes() if ln.allows("bus")), e.getLanes()[0])
            f.write(f'    <busStop id="{sid}" name="{nm}" lane="{lane.getID()}" '
                    f'startPos="{max(pos - 12, 0):.1f}" endPos="{min(pos + 3, e.getLength()):.1f}" friendlyPos="true"/>\n')
        f.write("</additional>\n")
    with open(rou_out, "w", encoding="utf-8") as f:
        f.write("<routes>\n" + "".join(rows) + "</routes>\n")
    return len(stops), len(rows)


if __name__ == "__main__":
    n_st, n_rt = build(os.path.join(HERE, "skku.net.xml"), os.path.join(HERE, "bus.rou.xml"),
                       os.path.join(HERE, "bus.stops.xml"))
    print(f"정류장 {n_st}곳, 버스 운행 {n_rt}개")
