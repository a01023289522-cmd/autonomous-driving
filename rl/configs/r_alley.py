"""한 대 폭 골목(bidi, 11/21) 환경. r_s8 설정 + 골목 일반 차량 통행 규칙(alley_gate) + 골목 입구 앞 출발 추가.
- 골목(서부로2123번길·율전로98번길)은 두 방향이 한 차로를 함께 쓴다 (sumo/skku_map/build.py ALLEY)
- 일반 차량은 반대 방향 차가 구간에 있으면 입구에서 기다린다 (sumo/skku_map/alley.py). AV는 학습으로 판단
- AV 관측: 골목 안이나 입구로 반대 방향 차가 있으면 '교차로 양보 상대' 칸에 들어간다 (관측 개수 41 그대로)
- 보상: 반대 방향 차가 있는데 골목 입구 교차로에 들어서면 양보 위반(yield_penalty 2, 기존 항 그대로)
- 출발점 섞기에 골목 입구 약 90 m 앞(7755484380#0)을 3번 더 넣어 골목 마주침 경험을 늘린다"""
from configs.r_s8 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, alley_gate=True, start_mix=list(_S["start_mix"]) + ["7755484380#0"] * 3)
