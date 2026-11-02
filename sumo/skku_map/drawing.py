"""화면 표현: 고가·지하차도 층 도형, 주차장·휴게소·지명, sumo-gui 보기 설정."""
from common import P, dashes, fmt, lane_z, side_line
from config import AREA, OSM
from highway import toll_booths


# 층 표현 (사용자 지정: 겹치는 곳에서는 높이(z)가 낮은 도로가 뒤쪽에, 낮은 층의 도로와 차는 옅게. 방안 A~D 화면 비교 후 'B 지도식' 선택)
#   sumo-gui는 도로망(차로·교차로 면)을 모두 같은 층(layer 0)에 그려 높이로 앞뒤를 가릴 수 없다
#   (userdoc/Simulation/Shapes.html "The network itself is drawn as layer 0").
#   → 보기 설정에서 고가(+3 m 넘음)·지하차도(-3 m 밑) 차로는 투명하게 두고, 그 두 층은 도형으로 직접 그린다.
#     지하차도 면: layer -0.5, 옅은 도로색 (배경 위, 도로망 밑 → 지상 도로·교차로 면에 가려짐)
#     지하차도 차선: layer 3.2 점선 (지상 도로·교차로 면 위로 비쳐 보이는 '숨은 선')
#     고가: 그림자 layer 15 + 진한 테두리 면 15.3 + 불투명 면 15.5 + 차선 15.8.
#       (layer 3.5에 두었더니 신호 교차로 면이 고가 위에 그려져 G1~G3에서 고가가 끊겨 보였다: 화면 확인 → 15로 올림)
#   차량은 도형보다 항상 위에 그려진다 → 아래층(지하차도, 고가 밑)의 차는 view_skku.py가 TraCI로 반투명하게 칠한다
BG_COLOR = (238, 236, 230)


ROAD_COLOR = (62, 62, 66)


UNDER_COLOR = ROAD_COLOR + (120,)          # 지하차도 면: 도로색을 바탕 위에 옅게 (불투명으로 변환해 씀)


UNDER_LINE = "95,95,100,230"


VIA_COLOR = (92, 100, 178)                # 고가 면 (불투명)


VIA_EDGE = "30,32,70"                     # 고가 테두리


VIA_SHADOW = "0,0,0,70"


VIA_LINE = "255,255,255,210"


def blend(c):
    a = c[3] / 255
    return ",".join(str(round(a * x + (1 - a) * b)) for x, b in zip(c[:3], BG_COLOR))


def layer_shapes(net):
    rows = []
    poly = lambda pid, kind, color, layer, pts, fill=True, lw=0.0: rows.append(
        f'    <poly id="{pid}" type="{kind}" color="{color}" fill="{int(fill)}" layer="{layer}"'
        + ("" if fill else f' lineWidth="{lw}"') + f' shape="{fmt(pts)}"/>\n')
    via = ",".join(map(str, VIA_COLOR))
    for e in net.getEdges():
        lanes = e.getLanes()
        z = lane_z(lanes[0])
        if -3 <= z <= 3:
            continue
        sh = [[p[:2] for p in ln.getShape()] for ln in lanes]
        right = side_line(sh[0], -lanes[0].getWidth() / 2)
        left = side_line(sh[-1], lanes[-1].getWidth() / 2)
        if z < -3:
            poly(f"under_{e.getID()}", "지하차도", blend(UNDER_COLOR), -0.5, left + right[::-1])
            lines = [left, right] + [side_line(s, ln.getWidth() / 2) for s, ln in zip(sh[:-1], lanes[:-1])]
            for i, ln_pts in enumerate(lines):
                for k, d in enumerate(dashes(ln_pts, 1.5, 1.5)):
                    poly(f"under_{e.getID()}_l{i}_{k}", "지하차도 (숨은 선)", UNDER_LINE, 3.2, d, False, 0.25)
        else:
            # 테두리는 면보다 0.6 m 넓은 진한 면을 밑(15.3)에 깔아 만든다: 고가 엣지 여러 개가 겹치거나 모이는 곳
            #   (덕영대로 고가 등)에서 선으로 그린 테두리가 면 안쪽으로 비쳐 지저분했다 → 면(15.5)이 안쪽 테두리를 덮는다
            outline = left + right[::-1]
            wide = (side_line(sh[-1], lanes[-1].getWidth() / 2 + 0.6)
                    + side_line(sh[0], -lanes[0].getWidth() / 2 - 0.6)[::-1])
            poly(f"via_{e.getID()}_sh", "고가 그림자", VIA_SHADOW, 15.0, [(x + 1.6, y - 1.6) for x, y in wide])
            poly(f"via_{e.getID()}_bd", "고가 테두리", VIA_EDGE, 15.3, wide)
            poly(f"via_{e.getID()}", "고가", via, 15.5, outline)
            for i, (s, ln) in enumerate(zip(sh[:-1], lanes[:-1])):
                for k, d in enumerate(dashes(side_line(s, ln.getWidth() / 2), 3, 5)):
                    poly(f"via_{e.getID()}_l{i}_{k}", "고가 차선", VIA_LINE, 15.8, d, False, 0.15)
    # 같은 층 엣지끼리만 만나는 노드의 교차로 면 (보기 설정에서 교차로 면은 지상 색이라 그 위를 같은 층 색으로 덮는다)
    for n in net.getNodes():
        es = n.getIncoming() + n.getOutgoing()
        if len(n.getShape()) < 3 or not es:
            continue
        zs = [lane_z(e.getLanes()[0]) for e in es]
        if all(z > 3 for z in zs):
            poly(f"via_j_{n.getID()}", "고가", via, 15.4, [p[:2] for p in n.getShape()])
        elif all(z < -3 for z in zs):
            poly(f"under_j_{n.getID()}", "지하차도", blend(UNDER_COLOR), -0.5, [p[:2] for p in n.getShape()])
    return rows


def write_additional(net):
    """주차장(parking.py) · 휴게소 · 지명 표시. 반환: 주차장별 parkingArea id 목록."""
    import json
    import parking
    rows, groups = parking.build(net, OSM, AREA, [tuple(p) for p in json.load(open(P("campus_poly.json")))])
    with open(P("skku.add.xml"), "w", encoding="utf-8") as f:
        f.write("<additional>\n")
        f.writelines(rows)
        for rest, lane in (("RS", "hw_rest_s_0"), ("RN", "hw_rest_n_0")):
            f.write(f'    <parkingArea id="{rest}" lane="{lane}" startPos="5" endPos="-5" roadsideCapacity="25" angle="45" '
                    f'name="의왕휴게소" friendlyPos="true"/>\n')
        dx = net.getNode("hS8").getCoord()[0] + 258                  # 고속도로를 옮긴 만큼 (highway())
        for pid, (x, y), text in (("sg", (25, 10), "SKKU Stn. Intersection"),
                                  ("tg", (-345 + dx, 2000), "Uiwang TG (toll)"),
                                  ("rest", (-330 + dx, 2580), "Uiwang rest area"), ("jc", (-258 + dx, 4400), "Hakui JC"),
                                  ("cg", (-258 + dx, 3450), "Cheonggye IC")):
            f.write(f'    <poi id="lbl_{pid}" type="{text}" x="{x + 15}" y="{y}" color="0,0,0,0" layer="100"/>\n')
        f.writelines(toll_booths(net))
        f.writelines(layer_shapes(net))
        f.write("</additional>\n")
    # 화면 설정 (userdoc/sumo-gui.html): 지상 차로만 진회색으로 그리고, 고가·지하차도 차로는 투명 ("by height at start").
    #   고가·지하차도는 layer_shapes()의 도형으로 층에 맞게 그린다. (예전 '지상만'·'고가만' 보기는 도형을 숨길 수 없어 뺐다)
    # 차는 실제 크기의 자동차 모양(simple shapes, 크기 고정 안 함)
    def scheme(name, under, ground, up):
        return (f'    <scheme name="{name}">\n        <background backgroundColor="238,236,230" showGrid="0"/>\n'
                f'        <edges laneEdgeMode="21" laneShowBorders="1">\n'
                f'            <colorScheme name="by height at start" interpolated="0">'
                f'<entry color="{under}" threshold="-100.00"/><entry color="{ground}" threshold="-3.00"/>'
                f'<entry color="{up}" threshold="3.00"/></colorScheme>\n        </edges>\n'
                f'        <junctions junctionMode="0"><colorScheme name="uniform"><entry color="{ground}"/>'
                f'<entry color="150,200,200" name="waterway"/><entry color="invisible" name="railway"/>'
                f'<entry color="200,240,240" name="airway"/></colorScheme></junctions>\n'   # 교차로 면도 도로와 같은 색
                '        <vehicles vehicleMode="0" vehicleQuality="2" vehicle_minSize="1.00" vehicle_exaggeration="1.00" '
                'vehicle_constantSize="0" showBlinker="1"/>\n'
                '        <pois poiType_show="1" poiType_size="55" poiType_color="45,45,60" poiType_constantSize="1"/>\n'
                '    </scheme>\n')
    with open(P("skku.gui.xml"), "w", encoding="utf-8") as f:
        f.write('<viewsettings>\n'
                + scheme("skku", "0,0,0,0", "62,62,66,255", "0,0,0,0")
                + '    <delay value="100"/>\n</viewsettings>\n')   # 한 스텝(0.2 s)마다 0.1 s 쉼 = 실제의 2배 빠르기
    return groups
