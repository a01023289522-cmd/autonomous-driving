"""봉담과천로(축소판 일자 고속도로): 의왕TG 요금소, 휴게소, 청계IC, 학의JC. 서부로 북쪽 끝에 그대로 이어진다."""
import math

from common import curve, fmt, unit


TOLL_BOOTHS = 10        # 의왕TG 한 방향 부스 수 (요금소는 실제 크기로, 줄인 것은 직선 구간뿐)


MERGE_AT = {"hS1", "hS3", "hS5", "hN4", "hN2"}      # 진입로가 바깥 차로(0번)로 합류하는 곳 (가속 차로)


EXIT_AT = {"hS2"}       # 진출로 앞 감속 차로: 바깥 차로(0번)는 진출로로만 (청계IC 남행 700대/h가 본선에서 차로를 못 바꿔 순간이동했다)


def plaza(y_from, booth=40, sign=-1):
    """요금소: 3차로가 한 번에 부드럽게 부스 수만큼 넓어지고(깔때기 모양 교차로 면), 부스 구간(40 km/h), 다시 3차로로 좁아진다.
    반환: [(노드 이름 뒤 번호, 그 노드에서 시작하는 구간의 y, 차로 수, km/h)], 끝 y (sign=-1 남쪽 방향, +1 북쪽 방향)"""
    t = taper_len(3, TOLL_BOOTHS)
    y0 = y_from + sign * t / 2                       # 넓어지는 깔때기 가운데
    y1 = y0 + sign * (t / 2 + booth + t / 2)         # 좁아지는 깔때기 가운데
    return [("0", y0, TOLL_BOOTHS, 40), ("1", y1, 3, 80)], y1 + sign * t / 2


def taper_len(n1, n2):
    """차로 수가 바뀌는 깔때기 길이: 차로 하나당 16 m (최소 40 m)."""
    return max(40.0, 16.0 * abs(n2 - n1))


def smooth(t):
    return t * t * (3 - 2 * t)


HW_LEAD = 350           # 고속도로 남쪽 끝: 서부로 북쪽 끝에서 서부로 방향 그대로 뻗는 길이 (그 뒤 곧게 북쪽으로)


def highway(sb_end, nb_start, north):
    """봉담과천로(사당 방면) 축소판. 실제 순서(카카오맵 길찾기·로드뷰 확인):
    과천 → 학의JC(합류) → 청계IC(진출·진입) → 의왕휴게소 → 의왕TG(톨게이트) → 서부로 → 사거리.
    본선 한 방향 3차로(로드뷰). 직선 구간만 줄였고 요금소는 실제처럼 부스 수만큼 넓어졌다 줄어든다.
    차로 수가 바뀌는 곳은 교차로 면을 깔때기 모양(노드 shape, userdoc/Networks/PlainXML.html)으로 만들어
    계단 없이 매끄럽게 넓어지고 좁아진다. 중앙분리대 쪽 가장자리는 곧게 두고 바깥쪽만 벌어진다.
    남쪽 끝은 서부로 북쪽 끝(구현 범위 경계 노드)에 그대로 이어진 일자 도로 (사용자 지정: 연결부는 사실적일 필요 없이
    일자 고속도로 역할만). 예전 의왕IC·서부로 연결로는 뺐다.
    sb_end / nb_start: (서부로 노드 id, (x, y)), north: 서부로 북쪽 방향 단위 벡터.
    반환: 노드 {이름: (x, y)}, 엣지, 차로 연결, 노드 모양 {이름: [(x, y)...]}, zipper 노드"""
    # 본선은 x = 상수인 세로선. 서부로 끝에서 north 방향으로 HW_LEAD 간 점의 x를 쓰고, 아래 좌표(램프 등)는 남쪽 방향 x = -258
    # 기준으로 적은 뒤 마지막에 통째로 옮긴다
    a_s = (sb_end[1][0] + north[0] * HW_LEAD, sb_end[1][1] + north[1] * HW_LEAD)
    a_n = (nb_start[1][0] + north[0] * HW_LEAD, nb_start[1][1] + north[1] * HW_LEAD)
    dx = a_s[0] + 258
    xs, xn = -258, -258 + (a_n[0] - a_s[0])
    W = 3.2

    def x_of(base, lanes, sgn):          # sgn: 남쪽 방향은 바깥이 서쪽(-), 북쪽 방향은 동쪽(+)
        return base + sgn * (lanes - 3) * W / 2

    nodes, E, shapes, zipper = {}, [], {}, set()

    C = []   # 본선 차로 연결 (from, to, fromLane, toLane): 0번이 가장 오른쪽(바깥) 차로

    def funnel(base, sgn, dy, yb, n1, n2):
        """차로 n1 → n2로 바뀌는 깔때기 모양 교차로 면 (가운데 yb, 진행 방향 dy = ±1)."""
        t = taper_len(n1, n2)
        inner = base - sgn * 1.5 * W
        outer = lambda n: base + sgn * (n - 1.5) * W
        side = [(outer(n1) + (outer(n2) - outer(n1)) * smooth(k / 10), yb - dy * t / 2 + dy * t * k / 10)
                for k in range(11)]
        return [(inner, side[0][1])] + side + [(inner, side[-1][1])]

    def chain(points, base, sgn, dy):
        """points: [(노드 이름, y, 이 노드에서 시작하는 구간 차로 수, km/h)] 차례로 잇는다.
        진입로 합류(MERGE_AT)는 바깥쪽(0번)에 가속 차로가 생긴다(기존 i → i+1).
        그 밖에 차로 수가 바뀌는 곳은 깔때기 교차로: 크게 바뀌면(요금소) 차로를 고르게 나눠 잇고,
        한 차로만 줄면 바깥 두 차로(0·1번)가 0번으로 합쳐진다. 줄어드는 곳은 zipper 교차로(번갈아 끼어들기,
        userdoc/Networks/PlainXML.html): 보통 교차로로 두면 합류 차로가 정지선에서 긴 깔때기 끝까지 비기를 기다려 막힌다."""
        segs = list(zip(points, points[1:]))
        for (a, ya, n, v), (b, yb, _, _) in segs:
            xa = x_of(base, n, sgn)
            E.append((f"hw_{a}_{b}", a, b, n, v, [(xa, ya), (xa, yb)]))
        for ((a, _, n1, _), (b, yb, _, _)), ((_, _, n2, _), (c, _, _, _)) in zip(segs, segs[1:]):
            e1, e2 = f"hw_{a}_{b}", f"hw_{b}_{c}"
            if n2 == n1:
                C.extend((e1, e2, i, i) for i in range(n1))
                continue
            if b in MERGE_AT:
                C.extend((e1, e2, i, i + n2 - n1) for i in range(n1))
                continue
            if b in EXIT_AT:                                # 0번(감속 차로)은 진출로로만, 나머지는 한 칸씩 안쪽으로
                C.extend((e1, e2, i, i - 1) for i in range(1, n1))
                continue
            shapes[b] = funnel(base, sgn, dy, yb, n1, n2)
            if abs(n2 - n1) > 1:                            # 요금소: 차로를 고르게 나눠 펼치고 모은다
                lo, hi = min(n1, n2), max(n1, n2)
                pairs = [(j * lo // hi, j) for j in range(hi)]
                C.extend((e1, e2, i, j) if n2 > n1 else (e1, e2, j, i) for i, j in pairs)
            elif n2 > n1:
                C.extend((e1, e2, i, i + 1) for i in range(n1))
                C.append((e1, e2, 0, 0))
            else:
                C.extend((e1, e2, i, max(i - 1, 0)) for i in range(n1))
            if n2 < n1:
                zipper.add(b)
        for name, y, _, _ in points:
            nodes[name] = (base, y)

    # 남쪽 방향(사당 → 봉담)
    sb = [("hS0", 5600, 3, 90), ("hS1", 4400, 4, 90), ("hS1b", 4100, 3, 90), ("hS1c", 3850, 4, 90), ("hS2", 3600, 3, 90),
          ("hS3", 3300, 4, 90), ("hS3b", 3100, 3, 90), ("hS4", 2700, 3, 90), ("hS5", 2450, 4, 90), ("hS5b", 2300, 3, 80)]
    steps, _ = plaza(2250, sign=-1)
    sb += [(f"hT{k}", y0, n, v) for k, y0, n, v in steps]
    sb += [("hS8", 1400, 3, 90), ("hS9", 1000, 3, 60), (sb_end[0], 0, 3, 60)]
    chain(sb, xs, -1, -1)
    # 북쪽 방향(봉담 → 사당)
    nb = [(nb_start[0], 0, 3, 60), ("hN9", 1000, 3, 90), ("hN8", 1400, 3, 90), ("hY2", 1720, 3, 80)]
    steps, _ = plaza(1750, sign=+1)
    nb += [(f"hU{k}", y0, n, v) for k, y0, n, v in steps]
    nb += [("hN5", 2450, 3, 90), ("hN4", 2700, 4, 90), ("hN4b", 2800, 3, 90),
           ("hN3", 3300, 3, 90), ("hN2", 3600, 4, 90), ("hN2b", 3800, 3, 90), ("hN1", 4400, 3, 90), ("hN0", 5600, 3, 90)]
    chain(nb, xn, +1, +1)
    # 이름 맞추기 (서부로와 잇는 끝 엣지: hw_hS9_bd, hw_bd_hN9)
    ren = {f"hw_hS9_{sb_end[0]}": "hw_hS9_bd", f"hw_{nb_start[0]}_hN9": "hw_bd_hN9"}
    E = [(ren.get(e, e), a, b, n, v, s) for e, a, b, n, v, s in E]
    C = [(ren.get(f, f), ren.get(t, t), i, j) for f, t, i, j in C]

    def lead_in(end, anchor, top):
        """서부로 끝 → anchor까지 서부로 방향 그대로 곧게 → 부드럽게 꺾여 → (본선 x, top)까지 곧게. 남쪽 방향 차례."""
        ax, ay = anchor[0] - dx, anchor[1]
        p0 = (end[0] - dx, end[1])
        v = (ax + (p0[0] - ax) * 120 / HW_LEAD, ay + (p0[1] - ay) * 120 / HW_LEAD)
        return curve([(ax, top), (ax, ay + 120), (ax, ay), v, p0], n=12)
    E = [(e, a, b, n, v, lead_in(sb_end[1], a_s, 1000) if e == "hw_hS9_bd"
          else lead_in(nb_start[1], a_n, 1000)[::-1] if e == "hw_bd_hN9" else s) for e, a, b, n, v, s in E]
    nodes.pop(sb_end[0])
    nodes.pop(nb_start[0])

    def ramp(eid, a, b, via, lanes, kmh):
        E.append((eid, a, b, lanes, kmh, curve([nodes[a], *via, nodes[b]])))

    nodes |= {"hJCs": (-700, 4800), "hJCn": (100, 4700),              # 학의JC (북행 진출은 오른쪽=동쪽으로)
              "hCGo": (250, 3450), "hCGi": (250, 3750),               # 청계IC 동쪽
              "hCGo2": (-650, 3450), "hCGi2": (-650, 3150),           # 청계IC 서쪽
              "hRs1": (-330, 2650), "hRs2": (-330, 2500), "hRn1": (-170, 2500), "hRn2": (-170, 2650)}  # 휴게소
    ramp("hw_jc_in", "hJCs", "hS1", [(-450, 4650), (-300, 4480)], 1, 60)
    ramp("hw_jc_out", "hN1", "hJCn", [(-215, 4500), (-120, 4640)], 1, 60)
    ramp("hw_cg_out", "hS2", "hCGo2", [(-285, 3520), (-420, 3460)], 1, 50)
    ramp("hw_cg_in", "hCGi2", "hS3", [(-420, 3170), (-285, 3240)], 1, 50)
    ramp("hw_cg_out2", "hN3", "hCGo", [(-215, 3380), (60, 3440)], 1, 50)
    ramp("hw_cg_in2", "hCGi", "hN2", [(60, 3740), (-215, 3660)], 1, 50)
    ramp("hw_rest_s_in", "hS4", "hRs1", [(-290, 2670)], 1, 40)
    ramp("hw_rest_s", "hRs1", "hRs2", [], 1, 20)
    ramp("hw_rest_s_out", "hRs2", "hS5", [(-290, 2470)], 1, 40)
    ramp("hw_rest_n_in", "hN5", "hRn1", [(-210, 2480)], 1, 40)
    ramp("hw_rest_n", "hRn1", "hRn2", [], 1, 20)
    ramp("hw_rest_n_out", "hRn2", "hN4", [(-210, 2680)], 1, 40)
    # 진입로 → 본선 바깥 차로(0번), 본선 바깥 차로 → 진출로
    after = {a: e for e, a, b, n, v, s in E if e.startswith("hw_h") and not e.startswith(("hw_hR",))}
    for ramp_id, node in (("hw_jc_in", "hS1"), ("hw_cg_in", "hS3"), ("hw_rest_s_out", "hS5"),
                          ("hw_rest_n_out", "hN4"), ("hw_cg_in2", "hN2")):
        C.append((ramp_id, after[node], 0, 0))
    before = {b: e for e, a, b, n, v, s in E if e.startswith("hw_h")}
    for ramp_id, node in (("hw_cg_out", "hS2"), ("hw_rest_s_in", "hS4"), ("hw_cg_out2", "hN3"),
                          ("hw_rest_n_in", "hN5"), ("hw_jc_out", "hN1")):
        C.append((before[node], ramp_id, 0, 0))
    C += [("hw_rest_s_in", "hw_rest_s", 0, 0), ("hw_rest_s", "hw_rest_s_out", 0, 0),
          ("hw_rest_n_in", "hw_rest_n", 0, 0), ("hw_rest_n", "hw_rest_n_out", 0, 0)]
    # 서부로와 잇는 끝: 서부로 차로 그대로 (i → i)
    C += [("hw_hS9_bd", "_sb", i, i) for i in range(3)] + [("_nb", "hw_bd_hN9", i, i) for i in range(3)]
    # 통째로 옮기기
    mv = lambda pts: [(p[0] + dx, *p[1:]) for p in pts]
    nodes = {k: (x + dx, y) for k, (x, y) in nodes.items()}
    E = [(e, a, b, n, v, mv(s)) for e, a, b, n, v, s in E]
    shapes = {k: mv(s) for k, s in shapes.items()}
    return nodes, E, C, shapes, zipper


def toll_booths(net):
    """요금소 모양: 부스 구간(시속 40 km) 차로 사이에 부스 섬(회색), 위에 반투명 지붕."""
    rows = []
    for e in net.getEdges():
        if not e.getID().startswith(("hw_hT", "hw_hU")) or e.getSpeed() > 12:
            continue
        lanes = [[p[:2] for p in ln.getShape()] for ln in e.getLanes()]
        (x0, y0), (x1, y1) = lanes[0][0], lanes[0][-1]
        ux, uy = unit(x1 - x0, y1 - y0)
        L = math.dist((x0, y0), (x1, y1))
        mid = [((ln[0][0] + ln[-1][0]) / 2, (ln[0][1] + ln[-1][1]) / 2) for ln in lanes]
        for k in range(len(mid) + 1):              # 차로 사이 + 양 끝 바깥쪽
            if k == 0:
                c = (2 * mid[0][0] - mid[1][0] + mid[0][0], 2 * mid[0][1] - mid[1][1] + mid[0][1])
                c = ((mid[0][0] + c[0]) / 2, (mid[0][1] + c[1]) / 2)
            elif k == len(mid):
                c = ((mid[-1][0] * 3 - mid[-2][0]) / 2, (mid[-1][1] * 3 - mid[-2][1]) / 2)
            else:
                c = ((mid[k - 1][0] + mid[k][0]) / 2, (mid[k - 1][1] + mid[k][1]) / 2)
            hl, hw = L * 0.35, 0.6
            box = [(c[0] + ux * a - uy * b, c[1] + uy * a + ux * b) for a, b in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))]
            rows.append(f'    <poly id="booth_{e.getID()}_{k}" type="요금소 부스" color="150,150,155" fill="1" layer="5" '
                        f'shape="{fmt(box + box[:1])}"/>\n')
        a, b = mid[0], mid[-1]
        span = math.dist(a, b) / 2 + 3
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        roof = [(cx + ux * s1 * 6 - uy * s2 * span, cy + uy * s1 * 6 + ux * s2 * span) for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        rows.append(f'    <poly id="roof_{e.getID()}" type="의왕TG 지붕" color="80,110,160,90" fill="1" layer="6" '
                    f'shape="{fmt(roof + roof[:1])}"/>\n')
    return rows
