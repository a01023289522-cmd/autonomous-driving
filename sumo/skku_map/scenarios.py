"""평가 난이도용 추가 교통 파일 (기본 교통 skku.rou.xml 등은 그대로 두고 그 위에 더한다).

    python -X utf8 scenarios.py          # scenario_*.rou.xml 생성
학습·평가 설정에서 SCENARIO["extra_routes"] = ["scenario_rb_jam.rou.xml"] 처럼 쓴다 (rl/skku_env.py가 추가 파일로 읽는다).

교통량 배율(SCENARIO["traffic_scale"], sumo --scale)만 올리면 회전교차로는 거의 막히지 않았다 (11/17 측정: 배율 1.6에서도
AV 진입로 대기 평균 0.1대). 그래서 회전교차로를 지나는 흐름을 AV가 도착하는 시간대에 몰아서 넣는다.
"""
import sumolib

import traffic
from common import P

# (이름, 지나야 할 엣지들, 시간당 대수, 시작 초, 끝 초). AV는 워밍업 600초 뒤 출발해 약 700~1000초에 회전교차로에 닿는다
SCENARIOS = {
    # AV 입구(율전로 북동쪽 갈래) 앞의 회전 구간을 지나는 이동만 늘린다 (도로망 경로로 확인: 율전로 서쪽·율전로63번길에서 들어와
    # 율전로 북동쪽으로 나가는 차). 율전로64번길 입구는 이미 대기 행렬이 있어 여기로 넣으면 투입이 밀리기만 했다
    "rb_jam": [
        ("rbj_west", ["5039133830#3", "5039133870#0"], 0, 550, 1300),
        ("rbj_63", ["-4526039560#0", "5039133870#0"], 0, 550, 1300),
        ("rbj_av", ["-5039133870#1", "-5039133870#0", "-5039133830#3"], 0, 550, 1300),   # AV와 같은 진입로: AV 앞에 줄이 서게
    ],
}
RB_JAM_VPH = {"rbj_west": 600, "rbj_63": 600, "rbj_av": 500}


def write(net, name, flows):
    rows = []
    for fid, via, vph, b, e in flows:
        vph = vph or RB_JAM_VPH[fid]
        src, dst = traffic.extend(net, via[0], True), traffic.extend(net, via[-1], False)
        mid = " ".join(v for v in via if v not in (src, dst))
        rows.append(f'    <flow id="{fid}" type="car" begin="{b}" end="{e}" period="exp({vph / 3600:.4f})" from="{src}" to="{dst}"'
                    + (f' via="{mid}"' if mid else "") + ' departLane="best" departSpeed="avg"/>\n')
    with open(P(f"scenario_{name}.rou.xml"), "w", encoding="utf-8") as f:
        f.write("<routes>\n" + "".join(rows) + "</routes>\n")
    print(f"scenario_{name}.rou.xml: 흐름 {len(rows)}개")


if __name__ == "__main__":
    net = sumolib.net.readNet(P("skku.net.xml"))
    for name, flows in SCENARIOS.items():
        write(net, name, flows)
