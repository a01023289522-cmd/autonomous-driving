"""r_tg 수정: 서 있는 대상(정지선·서 있는 앞차)의 목표 간격을 편안한 제동 거리 s0 + v²/(2·2.5)로, 멀리 섬 감점 0.05 → 0.1.
r_tg 30만(1000–1199 197/1/2, 하지만 정지선까지 중앙 31.3 m)에서 이어서."""
from configs.r_tg import SCENARIO, HPARAMS  # noqa: F401
from configs.r_tg import REWARD as _R
REWARD = dict(_R, tg_static_decel=2.5, tg_far=0.1)
