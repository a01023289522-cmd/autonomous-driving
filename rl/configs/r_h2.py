"""r_h1 + yield_near_m 5: 양보 연결 앞에서 우선 차량이 5 m 안에 있으면 서 있어도 위험(양보 위반 감점·양보 정지선 목표).
11/23 1단계 모델 남은 충돌 2건(495951808 좌회전): 교차 지점 2.6 m 앞에 서 있던 우선 차량을 TTC 무한대로 보고 진입 → 그 차가 출발."""
from configs.r_h1 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, yield_near_m=5.0)
