"""r_h13 + tg_far_scale 50→15 (11/23 임재성). js_h13d(25)는 정지선 6.61→5.33 m지만 충돌 21→28건이라 중간값을 본다."""
from configs.r_h13 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_far_scale=15.0)
