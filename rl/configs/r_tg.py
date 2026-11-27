"""목표 간격 하나로 상황별 땜질 항을 대체 (11/22, 사용자 승인). r_alley3b(골목 최종, 관측 43개) 기반.
- 추가: target_gap — 앞차·빨간불 정지선·양보할 차가 곧 오는 교차로 입구·반대 방향 차가 있는 골목 입구 중 가장 가까운 대상까지
  목표 간격 s* = s0 + 1.2 s·v + IDM 접근 항. 가까우면 tg_close(0.1) 비례, 서 있는 대상보다 멀면 tg_far(0.05) 비례 감점
- 끔: 수업 6 m 간격 감점(close_gap_penalty 0), 2초 간격(headway_s 0), 빨간불 접근 보상(red_approach 0).
  정차 감점은 대상이 없을 때(빈 도로에서 섬)만. queue_fix는 막힘 감점 되돌림(버스 뒤 대기)용으로 유지
- 유지: 충돌, 신호 위반, 양보 위반(골목 포함), 과속, 막힘, 차로 변경"""
from configs.r_alley3b import SCENARIO, HPARAMS  # noqa: F401
from configs.r_alley3b import REWARD as _R
REWARD = dict(_R, target_gap=True, tg_close=0.1, tg_far=0.05, close_gap_penalty=0.0, headway_s=0.0, red_approach=0.0)
