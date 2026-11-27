"""r_tg2 + 목표 간격 적용 범위 50 → 100 m (tg_range). 11/22 r_tg2 30만: 정문 앞 일월로에서 정지선 69.7 m 앞에 섬 — 50 m 밖이면
목표 간격 감점이 없고 약한 정차 감점만 받는 빈틈. 신호 관측 범위(100 m)와 맞춘다. 정지선까지 거리는 100 m 안이면 관측에 있음."""
from configs.r_tg2 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_tg2 import REWARD as _R
REWARD = dict(_R, tg_range=100.0)
