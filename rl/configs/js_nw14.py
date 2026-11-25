"""js_nw7 + tg_red_stop_bonus 2 (11/25 임재성). 빨간·노란불 정지선 6 m 안에 앞차 없이 멈추면 신호마다 1회 +2.
nw7을 10만 넘게 학습하면 정지선에서 점점 멀리 섬(2.7 → 28 m) → 1회 보너스로 정지선 쪽으로 당긴다. js_nw7_100k에서 이어 학습."""
from configs.js_nw7 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_red_stop_bonus=2.0, tg_red_stop_max=6.0)
