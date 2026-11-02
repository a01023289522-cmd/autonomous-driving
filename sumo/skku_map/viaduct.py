"""서부로 고가(밤밭고가) 구간: 고가 가운데선, 고가 옆 지상 도로 띄우기, 공영주차장 띠 자리."""
import math

from common import curve, fmt, lane_z, offset_line, poly_point, poly_project, smoothstep, unit
from config import GAPS, LOT_IN, NB, SB


# 고가 가운데선 (OSM 고가 두 방향 선의 가운데)
CL = [(0, 0), (0, -25), (-6, -68), (-26, -127), (-39, -154), (-60, -188), (-91, -226), (-118, -266),
      (-138, -298), (-153, -326), (-169, -358), (-185, -396), (-197, -433), (-205, -465), (-221, -536),
      (-230, -598), (-234, -660), (-241, -797)]


# 서부로 고가(밤밭고가): 사거리에서 시작해 철길 위 다리를 지나 삼성아파트 앞까지 끊김 없이 한 방향 2차로씩 (위성사진 2+2).
#   OSM에는 철길 위 ~ G1 구간이 4차로로 적혀 두 방향이 서로 겹쳐 있었다 → 고가 가운데선(CL)에서 분리대 1 m를 두고
#   양쪽 2차로로 다시 그린다. 철길 위에서는 고가 바깥에 지상으로 내려가는 1차로가 맞닿아 붙는다 (한 덩어리 넓은 다리).
#   (사거리 쪽 엣지 → 남쪽 끝 엣지 순서, 중간 노드)
VIA_SB = ["6003174920", "6003174900", "4883925510"]


VIA_NB = ["4948457660", "6003174910", "6003174890"]


RAMP_SB, RAMP_NB = ("700812830", "4807018640"), ("4883933160", "4807018641")   # 다리 위 지상 내려가는 길 (엣지, 끝 노드)


VIA_S = (70, 135)                                           # OSM 중간 노드 위치 (CL 길이): 철길 남쪽 끝, G1 근처


GAP = 3.0               # 고가 양옆 지상 서부로를 고가에서 일부러 띄우는 거리 (m): 화면에서 다른 층으로 보이게 (사용자 지정 2026-11-02)


VIA_HALF = 0.5 + 6.4    # 고가 가운데선에서 고가 바깥 가장자리까지 (분리대 반 + 2차로)


LOT_AISLE = 10.5        # 고가 밑 공영주차장 통로 가운데선: 고가 바깥 가장자리 + 2 m(테두리·그림자 포함) + 통로 반폭 (사용자 지정: 고가와 떨어진 양옆 띠로)


LOT_EDGE = 18.8         # 주차장 띠가 있는 쪽 지상 도로 안쪽 가장자리: 통로 3.2 m + 직각 주차 칸 5.2 m + 도로와 1.5 m


#   (도로·고가에 딱 붙이면 주차장이 도로의 한 차로처럼 보였다: 사용자 지적)
LOT_RAMP = 60.0         # 주차장 구간 앞뒤에서 도로가 서서히 바깥으로 비켜나는 길이 (짧으면 차가 꿈틀거린다)


def corridor_moves(net, cl, lot_spans):
    """고가 양옆을 나란히 달리는 지상 엣지를 바깥으로 옮긴 모양 {엣지: 점들}.
    차로 안쪽 가장자리가 고가 가운데선에서 VIA_HALF + GAP (주차장 띠가 있는 쪽·구간은 LOT_EDGE) 이상 떨어지게 민다.
    lot_spans: [(s 시작, s 끝, 쪽)] 쪽 +1 = 서쪽(가운데선 진행 방향 오른쪽), -1 = 동쪽.
    옮기지 않는 길과 이어지는 끝은 30 m에 걸쳐 원래 자리로 서서히 돌아간다 (한 번에 꺾으면 차가 꿈틀거렸다)."""
    L = sum(math.dist(a, b) for a, b in zip(cl, cl[1:]))

    lo = VIA_S[0] + 5 + LOT_RAMP                          # 철길 위 다리(고가 옆 1차로가 붙은 곳)가 끝난 뒤부터 비켜난다
    hi = max(max(a, b) for a, b, _ in lot_spans) + 15
    assert lo <= min(min(a, b) for a, b, _ in lot_spans), "주차장 띠 시작 전에 도로가 다 비켜나야 한다"

    def need(s, side):
        # 주차장 띠 폭만큼 떨어진 거리를 고가 구간 내내 양쪽 똑같이 유지하고, 비켜나는 곳은 그 앞뒤 두 군데만 길게.
        #   (주차장마다 도로가 들쭉날쭉 비켜나게 했더니 S자 굴곡이 잦아 차가 계속 꿈틀거렸다: 사용자 지적)
        w = smoothstep((s - (lo - LOT_RAMP)) / LOT_RAMP) * smoothstep(((hi + LOT_RAMP) - s) / LOT_RAMP)
        return VIA_HALF + GAP + (LOT_EDGE - VIA_HALF - GAP) * w

    raw, side_of = {}, {}
    for e in net.getEdges():
        if (e.getID() in (RAMP_SB[0], RAMP_NB[0], *VIA_SB, *VIA_NB)
                or abs(e.getShape()[0][2] if len(e.getShape()[0]) > 2 else 0) > 3 or not e.allows("passenger")):
            continue
        sh = [p[:2] for p in e.getShape()]
        ss = [poly_project(cl, p) for p in sh]
        near = [math.dist(p, poly_point(cl, s)) for p, s in zip(sh, ss)]
        inside = [k for k, s in enumerate(ss) if 1 < s < L - 1]
        if len(inside) < 0.5 * len(ss) or max(near[k] for k in inside) > 22:
            continue                                      # 고가 남쪽 끝을 넘어가는 엣지도 대상 (넘어간 부분은 아래에서 서서히 0)
        a, b = poly_point(cl, ss[0]), poly_point(cl, ss[-1])
        if math.dist(sh[0], sh[-1]) > 3 and abs(sum(x * y for x, y in zip(
                unit(sh[-1][0] - sh[0][0], sh[-1][1] - sh[0][1]), unit(b[0] - a[0], b[1] - a[1])))) < 0.85:
            continue                                      # 가로지르는 길은 그대로 (아주 짧은 연결 토막은 함께 옮긴다)
        half = e.getLaneNumber() * 3.2 / 2
        pts, sides = [], []
        for p, s, d in zip(sh, ss, near):
            q = poly_point(cl, s)
            u = unit(*[y - x for x, y in zip(poly_point(cl, max(0, s - 1)), poly_point(cl, min(L, s + 1)))])
            side = 1 if (p[0] - q[0]) * u[1] - (p[1] - q[1]) * u[0] > 0 else -1
            m = max(0.0, need(s, side) - (d - half)) * smoothstep((L - 1 - s) / 40)
            pts.append((p[0] + u[1] * side * m, p[1] - u[0] * side * m))
            sides.append(side)
        raw[e.getID()] = pts
        side_of[e.getID()] = max(set(sides), key=sides.count)
    # 같은 쪽의 옮긴 길(또는 같이 옮긴 다리 위 1차로)과 이어지지 않는 끝은 서서히 원래 자리로
    ramp_side = {RAMP_SB[0]: 1, RAMP_NB[0]: -1}
    out = {}
    for eid, pts in raw.items():
        e = net.getEdge(eid)
        sd = side_of[eid]
        joined_in = any(i.getID() in raw and side_of[i.getID()] == sd or ramp_side.get(i.getID()) == sd
                        for i in e.getFromNode().getIncoming())
        joined_out = any(o.getID() in raw and side_of[o.getID()] == sd or ramp_side.get(o.getID()) == sd
                         for o in e.getToNode().getOutgoing())
        sh = [p[:2] for p in e.getShape()]
        Ls = sum(math.dist(a, b) for a, b in zip(sh, sh[1:]))
        T = max(1.0, min(30.0, Ls * 0.8))
        acc, res = 0.0, []
        for k, (p, m) in enumerate(zip(sh, pts)):
            if k:
                acc += math.dist(sh[k - 1], p)
            f = (1.0 if joined_in else smoothstep(acc / T)) * (1.0 if joined_out else smoothstep((Ls - acc) / T))
            res.append((p[0] + (m[0] - p[0]) * f, p[1] + (m[1] - p[1]) * f))
        # 길이가 짧아 점이 적은 엣지는 서서히 돌아가는 구간에 점을 더 넣어야 곡선이 된다
        if not (joined_in and joined_out) and len(sh) < 8 and Ls > 8:
            dense = [poly_point(sh, Ls * k / 8) for k in range(9)]
            res = []
            for k, p in enumerate(dense):
                acc = Ls * k / 8
                s = poly_project(cl, p)
                q = poly_point(cl, s)
                u = unit(*[y - x for x, y in zip(poly_point(cl, max(0, s - 1)), poly_point(cl, min(L, s + 1)))])
                d = math.dist(p, q)
                m = max(0.0, need(s, sd) - (d - e.getLaneNumber() * 1.6)) * smoothstep((L - 1 - s) / 40)
                f = (1.0 if joined_in else smoothstep(acc / T)) * (1.0 if joined_out else smoothstep((Ls - acc) / T))
                res.append((p[0] + u[1] * sd * m * f, p[1] - u[0] * sd * m * f))
        out[eid] = res
    return out


def road_cut(net, moved, p, d):
    """점 p에서 가장 가까운, d 방향으로 달리는 지상 서부로 엣지와 그 위의 길이 (양 끝 4 m는 피함)."""
    best = None
    for e in net.getEdges():
        if e.getName() != "서부로" or e.getID() in (RAMP_SB[0], RAMP_NB[0], *VIA_SB, *VIA_NB) or abs(lane_z(e.getLanes()[0])) > 3:
            continue
        sh = moved.get(e.getID()) or [q[:2] for q in e.getShape()]
        L = sum(math.dist(a, b) for a, b in zip(sh, sh[1:]))
        s = poly_project(sh, p)
        a, b = poly_point(sh, max(0.0, s - 2)), poly_point(sh, min(L, s + 2))
        if L < 10 or sum(x * y for x, y in zip(unit(b[0] - a[0], b[1] - a[1]), d)) < 0.7:
            continue
        dist = math.dist(p, poly_point(sh, s))
        if best is None or dist < best[0]:
            best = (dist, e.getID(), max(4.0, min(L - 4.0, s)))
    return best[1], best[2]


def lots_and_side_roads(net, pt):
    """공영주차장 3곳의 통로·드나드는 길, 고가 옆 지상 서부로 띄우기, 주차장 드나드는 곳에서 도로 자르기."""
    # 고가 밑 공영주차장 3곳 (카카오맵 장소 좌표·'입구' 표시 + 사용자 로드뷰 사진 2026-10-29).
    #   실제로는 고가 밑이지만, 화면에서 고가와 구분되도록 고가 바깥 양옆(지상 도로 쪽) 띠에 통로 + 평행 주차 칸으로 둔다 (사용자 지정 2026-11-03)
    #   들고 나는 곳은 지상 서부로를 그 자리에서 잘라 붙인다 (신호 교차로로 바로 드나들면 신호 계획에 칸이 없어 막힌다)
    #   P1 율전제3공영 (G1~G2, 동쪽 띠): G2 북쪽 북행 도로에서 진입(카카오 입구, 로드뷰) → 북쪽으로 → G1 앞 북행 도로로 (출구는 미확인)
    #   P2 율전공영(다리밑) (G2~G3, 서쪽 띠): G2 남쪽 남행 도로에서 진입(카카오 입구) → 남쪽으로 → G3 앞 남행 도로로 ('출구전용·좌회전 금지')
    #   P3 율전 제2공영 (G3 남쪽, 동쪽 띠): 남쪽 끝에서 남행 도로 좌회전으로 고가 밑을 건너 진입(로드뷰) → 북쪽으로 → G3 남쪽 북행 도로로 (차단기)
    cl = CL + [(-244, -850)]
    S = {k: poly_project(CL, p) for k, p in GAPS.items()}
    s1, s2 = poly_project(CL, LOT_IN["P1"]), poly_project(CL, LOT_IN["P2"])
    #       (주차장, 쪽(+1 서쪽 / -1 동쪽), 통로 시작 s, 통로 끝 s, 입구 쪽 도로 방향·도로 위 s, 출구 쪽 도로 방향·도로 위 s)
    lots = [("P1", -1, s1, S["G1"] + 25, (NB, s1 + 12), (NB, S["G1"] + 13)),
            ("P2", 1, s2 + 10, S["G3"] - 38, (SB, s2), (SB, S["G3"] - 27)),     # 입구·출구는 G2·G3 교차로에서 20 m 넘게 (붙이면 1 m 토막이 생긴다)
            ("P3", -1, S["G3"] + 200, S["G3"] + 30, (SB, S["G3"] + 190), (NB, S["G3"] + 18))]
    # 고가 옆 지상 서부로(양쪽)를 고가에서 띄운다 (주차장 띠가 있는 곳은 더): 화면에서 고가와 다른 층이라는 게 보이도록 (사용자 지정)
    moved = corridor_moves(net, cl, [(a_s, b_s, side) for _, side, a_s, b_s, _, _ in lots])
    cuts = {}                                             # 도로 엣지 → [(엣지 위 길이, 새 노드)]
    lot_edges = []
    for lot, side, a_s, b_s, (d_in, r_in), (d_out, r_out) in lots:
        aisle = offset_line(CL, side * LOT_AISLE, a_s, b_s, step=5.0)
        a, b = aisle[0], aisle[-1]
        pt.nod += [f'<node id="{lot}i" x="{a[0]:.2f}" y="{a[1]:.2f}"/>', f'<node id="{lot}o" x="{b[0]:.2f}" y="{b[1]:.2f}"/>']
        road = {}
        for tag, d, r in (("e", d_in, r_in), ("x", d_out, r_out)):
            eid, s = road_cut(net, moved, poly_point(CL, r), d)
            cuts.setdefault(eid, []).append((s, f"{lot}{tag}"))
            road[tag] = poly_point(moved.get(eid) or [q[:2] for q in net.getEdge(eid).getShape()], s)
        in_shape = ""
        if (side > 0) != (d_in == SB):                      # 반대편 도로에서 고가 밑을 건너 들어간다 (P3): U자로 돌아 통로로
            c1, c2 = offset_line(CL, 3.0, a_s + 7, a_s + 7)[0], offset_line(CL, -5.0, a_s + 7, a_s + 7)[0]
            in_shape = f' shape="{fmt(curve([road["e"], c1, c2, a], n=8))}"'
        lot_edges += [f'<edge id="{lot}_in" from="{lot}e" to="{lot}i" numLanes="1" speed="5.56" allow="taxi"{in_shape}/>',
                      f'<edge id="{lot}_aisle" from="{lot}i" to="{lot}o" numLanes="1" speed="4.17" allow="taxi" '
                      f'spreadType="center" shape="{fmt(aisle)}"/>',      # center: 통로가 정한 선 위에 (기본값이면 1.6 m 밀린다)
                      f'<edge id="{lot}_out" from="{lot}o" to="{lot}x" numLanes="1" speed="5.56" priority="1" allow="taxi"/>']
    pt.edg += lot_edges
    pt.deleted |= set(cuts)
    for eid in sorted(set(moved) | set(cuts)):
        e = net.getEdge(eid)
        sh = moved.get(eid) or [p[:2] for p in e.getShape()]
        if eid not in cuts:
            pt.edg.append(f'<edge id="{eid}" shape="{fmt(sh)}"/>')
            continue
        # 엣지를 자른 점마다 노드를 두고 조각 엣지로 다시 만든다 (차로·속도·허용 차종은 그대로)
        perm = " ".join(sorted(e.getLanes()[0].getPermissions()))
        common = (f'numLanes="{e.getLaneNumber()}" speed="{e.getSpeed():.2f}" priority="{e.getPriority()}" allow="{perm}" '
                  f'name="{e.getName()}" spreadType="center"')     # OSM 일방 도로와 같게 (빠뜨리면 차로가 한 칸 옆으로 밀린다)
        marks = sorted(cuts[eid])
        ends = [e.getFromNode().getID()] + [n for _, n in marks] + [e.getToNode().getID()]
        pos = [0.0] + [s for s, _ in marks] + [None]
        for (s, n) in marks:
            # 교차로 면은 도로 방향에 맞춘 폭 2 m 직사각형 (그대로 두면 비스듬히 붙는 주차장 길 때문에 면이 비뚤어져 정지선이 계단처럼 보였다)
            m = poly_point(sh, s)
            ux, uy = unit(*[q - p for p, q in zip(poly_point(sh, s - 1), poly_point(sh, s + 1))])
            w = e.getLaneNumber() * 3.2 / 2 + 0.2
            box = [(m[0] + ux * a - uy * b, m[1] + uy * a + ux * b) for a, b in ((-1, -w), (1, -w), (1, w), (-1, w))]
            pt.nod.append(f'<node id="{n}" x="{m[0]:.2f}" y="{m[1]:.2f}" type="priority" shape="{fmt(box)}"/>')
        pt.edg.append(f'<delete id="{eid}"/>')
        for k in range(len(ends) - 1):
            lo, hi = pos[k], pos[k + 1] if pos[k + 1] is not None else 1e9
            piece = ([poly_point(sh, lo)] + [p for p in sh if lo + 0.5 < poly_project(sh, p) < hi - 0.5]
                     + [poly_point(sh, min(hi, sum(math.dist(p, q) for p, q in zip(sh, sh[1:]))))])
            pt.edg.append(f'<edge id="{eid}_{"abcdefg"[k]}" from="{ends[k]}" to="{ends[k + 1]}" {common} shape="{fmt(piece)}"/>')
            pt.con.append(f'<connection from="{eid}_{"abcdefg"[k]}" reset="true"/>')
        pt.touched |= {e.getFromNode().getID(), e.getToNode().getID()}
    pt.fixed |= (set(moved) | {f"{eid}_{c}" for eid in cuts for c in "abcdefg"}
             | {f"{lot}_{k}" for lot, *_ in lots for k in ("in", "aisle", "out")})   # 높이 판정에서 빼기 (고가 선 옆이라 고가로 잡혔다)


def viaduct_edges(net, pt):
    # 서부로 고가: 가운데선에서 분리대 1 m + 2차로(남쪽 방향은 서쪽, 북쪽 방향은 동쪽), 높이 6 m로 끊김 없이.
    #   철길 위(s 0~70)에서는 바깥에 지상으로 내려가는 1차로가 맞닿아 붙는다 (높이 0으로 두어 고가와 색으로 구분)
    cl = CL + [(-244, -850)]
    half = 0.5 + 3.2                                        # 분리대 반 + 차로 하나 = 2차로 엣지 가운데선
    for ids in (VIA_SB, VIA_NB, RAMP_SB, RAMP_NB):
        for i in ids:
            if not (net.hasEdge(i) or net.hasNode(i)):
                raise SystemExit(f"서부로 고가 구성 요소를 못 찾음: {i} (OSM이 바뀌었으면 VIA_* 다시 확인)")
    sb_end = poly_project(cl, net.getEdge(VIA_SB[-1]).getToNode().getCoord()[:2])
    nb_end = poly_project(cl, net.getEdge(VIA_NB[0]).getFromNode().getCoord()[:2])
    # OSM은 고가를 방향마다 세 토막(사거리~철길 남쪽 끝~G1~남쪽 끝)으로 나눴는데, 중간 노드 둘은 OSM에서 다른 길과
    # 겹쳐 있어 dead_end로 잡혀 고가가 거기서 끊겨 있었고(연결 없음), 이어 붙여도 노드 자리에 줄이 남는다
    # → 방향마다 사거리에서 남쪽 끝까지 엣지 하나(via_sb, via_nb)로 다시 만든다
    first, last = net.getEdge(VIA_SB[0]), net.getEdge(VIA_SB[-1])
    common = (f'numLanes="2" speed="{first.getSpeed():.2f}" priority="{first.getPriority()}" type="{first.getType()}" '
              f'name="서부로" spreadType="center"')
    sh = offset_line(cl, half, 0, sb_end)
    pt.edg += [f'<delete id="{e}"/>' for e in VIA_SB + VIA_NB]
    pt.edg.append(f'<edge id="via_sb" from="{first.getFromNode().getID()}" to="{last.getToNode().getID()}" {common} '
               f'shape="{fmt([(x, y, 6) for x, y in sh])}"/>')
    first, last = net.getEdge(VIA_NB[0]), net.getEdge(VIA_NB[-1])
    sh = offset_line(cl, -half, nb_end, 0)
    pt.edg.append(f'<edge id="via_nb" from="{first.getFromNode().getID()}" to="{last.getToNode().getID()}" {common} '
               f'shape="{fmt([(x, y, 6) for x, y in sh])}"/>')
    pt.fixed |= {"via_sb", "via_nb", *VIA_SB, *VIA_NB}
    for nid in (net.getEdge(VIA_SB[0]).getFromNode().getID(), net.getEdge(VIA_SB[-1]).getToNode().getID(),
                net.getEdge(VIA_NB[0]).getFromNode().getID()):    # 새 엣지가 붙는 교차로: 연결 다시 계산
        pt.con += [f'<connection from="{e.getID()}" reset="true"/>' for e in net.getNode(nid).getIncoming()
                if e.getID() not in VIA_SB + VIA_NB]
    ramp_off = 0.5 + 6.4 + 1.6 + GAP                      # 고가 2차로 바깥 1차로 가운데선 (다른 지상도로처럼 GAP만큼 띄움)
    for (eid, nid), d, s0, s1 in ((RAMP_SB, ramp_off, 0, VIA_S[0]), (RAMP_NB, -ramp_off, VIA_S[0], 0)):
        sh = offset_line(cl, d, s0, s1)
        end = sh[-1] if s1 else sh[0]
        pt.nod.append(f'<node id="{nid}" x="{end[0]:.2f}" y="{end[1]:.2f}"/>')
        pt.edg.append(f'<edge id="{eid}" shape="{fmt([(x, y, 0) for x, y in sh])}"/>')
        pt.fixed.add(eid)
