"""데이터 칼럼 정의. make_column_sample.py(과제 예시)와 collect_columns.py(최종 수집)가 같이 쓴다.

필수 칼럼 19개(조교 공개, 삭제 불가) 뒤에 팀 칼럼을 붙인다.
  - 신호등 7개마다 독립된 숫자 칼럼 2개 (11/17 교수님 피드백: 신호 하나당 독립 칼럼, 문자열 금지)
      tls_<이름>_phase  : 현재 현시 번호 (정수). 현시 번호 ↔ 방향별 신호색은 신호 계획이 고정이라 표 하나로 정해진다
                          (python -X utf8 rl/columns.py 로 표 출력)
      tls_<이름>_remain : 현시가 바뀌기까지 남은 시간 (초)
  - event.red_light : 이번 스텝에 빨간불에서 교차로에 들어갔는가 (신호 위반. 다른 칼럼으로 계산할 수 없어 따로 둔다)
  - route.lane_changes : 경로를 따라가려면 필요한 차로 변경 수 (+ 왼쪽, - 오른쪽). 경로는 정해 주되 언제 바꿀지는 정책이 정한다
    (11/17 컨설팅: "이동해야 하는 차선 변경 수" 칼럼 권장)
state 칼럼(JSON)은 AV 반경 100 m 차량마다 차종·진행 방향·가속도·방향지시등·제동등을, AV마다 차로 수·제한속도·
다음 교차로까지 거리·양보 여부를 담는다 (rl/skku_env.py get_privileged_state). 데이터만으로 주행 중인 도로 상황을 다시 그릴 수 있게.
"""
import json

import numpy as np

REQUIRED = ["episode", "t", "observation", "action_raw", "action.accel_raw", "action.lane_change_raw", "action.lane_change",
            "action.lane_change_applied", "reward", "terminated", "truncated", "state", "detected_vehicles", "event.collided",
            "event.arrived", "event.lane_before", "event.lane_after", "next_observation", "next_state"]

# 이름: (신호 ID, 위치 설명). 경로 순서대로, 경로 밖 신호는 마지막
TLS = {
    "hayul":     ("cluster_495951062_5357160054", "서부로×하률로 (출발 직후, 경로 1번째 신호)"),
    "sageori":   ("cluster_4650845824_4655421093_4662858740_4662858741_#2more", "성대역 사거리"),
    "crosswalk": ("726912998", "서부로 횡단보도 (사거리 남쪽)"),
    "seobu2123": ("cluster_1184134292_726912991_837163934", "서부로×서부로2123번길 (골목 진입)"),
    "ilwol":     ("cluster_452394408_4871043595", "서부로×일월로"),
    "gate":      ("520991292", "일월로×학교 정문"),
    "seobu2105": ("cluster_4637428747_495943443", "서부로×서부로2105번길 (경로 밖)"),
}
ROAD_NAMES = {"15379779810#1": "정문 진입로", "700812840#2": "서쪽 골목"}
TEAM = [f"tls_{n}_{k}" for n in TLS for k in ("phase", "remain")] + ["event.red_light", "route.lane_changes"]
COLUMNS = REQUIRED + TEAM


def rnd(x):
    if isinstance(x, (float, np.floating)):
        return round(float(x), 3)
    if isinstance(x, dict):
        return {k: rnd(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v) for v in x]
    return x


def js(x):
    return json.dumps(rnd(x), ensure_ascii=False, separators=(",", ":"))


def tls_values(traci):
    """신호 7개의 (현시 번호, 남은 초)를 TEAM 칼럼 순서대로."""
    now, out = traci.simulation.getTime(), []
    for tid, _ in TLS.values():
        out += [traci.trafficlight.getPhase(tid), round(traci.trafficlight.getNextSwitch(tid) - now, 1)]
    return out


_next_state = {}


def step_row(env, traci, episode, t, obs, action):
    """한 스텝을 진행하고 (칼럼 한 줄, next_obs, term, trunc, info)를 돌려준다. 신호 칼럼은 행동을 정하기 전 시점(state와 같은 시점) 값.
    state는 직전 스텝의 next_state와 같은 시점이므로 다시 계산하지 않는다."""
    state = _next_state.pop(id(env)) if t > 0 and id(env) in _next_state else js(env.get_privileged_state())
    seen, tls, lane_changes = env.get_detected_vehicles(), tls_values(traci), env.route_lane_changes()
    next_obs, reward, term, trunc, info = env.step(action)
    next_state = js(env.get_privileged_state())
    if not (term or trunc):
        _next_state[id(env)] = next_state
    row = [episode, t, js(obs), js(action), rnd(info["accel_raw"]), rnd(info["lane_change_raw"]), info["lane_change"],
           info["lane_change_applied"], rnd(reward), term, trunc, state, js(seen), info["collided"], info["arrived"],
           info["lane_before"], info["lane_after"], js(next_obs), next_state, *tls, info.get("red_light", False), lane_changes]
    return row, next_obs, term, trunc, info


def phase_table(net_path):
    """신호마다 현시 번호 → 이름, 녹색 시간, 방향별 신호색 (칼럼 설명 자료용)."""
    import sumolib
    net = sumolib.net.readNet(net_path, withPrograms=True)
    lines = []
    for name, (tid, desc) in TLS.items():
        tl = net.getTLS(tid)
        lines.append(f"\n## tls_{name}: {desc}")
        links = {}
        for in_lane, out_lane, idx in tl.getConnections():
            e = in_lane.getEdge()
            c = [c for c in e.getConnections(out_lane.getEdge()) if c.getFromLane() == in_lane and c.getToLane() == out_lane][0]
            (x0, y0), (x1, y1) = in_lane.getShape()[-2:]
            way = max((("동행", x1 - x0), ("서행", x0 - x1), ("북행", y1 - y0), ("남행", y0 - y1)), key=lambda kv: kv[1])[0]
            turn = {"s": "직진", "l": "좌회전", "L": "좌회전", "r": "우회전", "R": "우회전", "t": "유턴"}.get(c.getDirection(), c.getDirection())
            links.setdefault(idx, f"{e.getName() or ROAD_NAMES.get(e.getID(), e.getID())} {way} {turn}")
        for i, p in enumerate(list(tl.getPrograms().values())[0].getPhases()):
            go = sorted({links[k] for k, ch in enumerate(p.state) if ch in "Gg" and k in links})
            label = p.name or ("황색" if "y" in p.state else "보행자 신호 (차량 전체 적색)" if set(p.state) <= {"r"} else "")
            lines.append(f"{i}: {label} {p.duration:.0f}초 | 녹색: {', '.join(go) or '없음'}")
    return "\n".join(lines)


if __name__ == "__main__":
    import os
    import course
    print(phase_table(os.path.join(course.TEAM, "sumo", "skku_map", "skku.net.xml")))
