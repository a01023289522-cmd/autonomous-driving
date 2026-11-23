"""r_h13 + tg_far_scale 50→15 (11/23 임재성). js_h13d(25)는 정지선 6.61→5.33 m지만 충돌 21→28건이라 중간값을 본다.
결과 (r_h13_25k에서 5만 학습, 3만 체크포인트 = models/js_h13e_30k.pt, 시드 2000–2999):
  r_h13 979/21, 정지선 6.61 m, 앞차 7.05 m → js_h13e 30k 982/18 (충돌 1.8%), 정지선 5.53 m, 앞차 7.61 m."""
from configs.r_h13 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_far_scale=15.0)
