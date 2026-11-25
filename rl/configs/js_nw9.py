"""js_nw7 + tg_far_red 0.2 (11/25 임재성). nw7 시드 1000–1199: 10만 = 빨간불 0·충돌 5·정지선 2.4 m, 15만 = 빨간불 0·충돌 6·정지선 7.3 m(20 m 넘게 123/935).
멀리 섬 감점을 0으로 두면 정지선에 다가갈 이유가 없어 학습이 길어질수록 멀리 섬 → 약하게 되살림. 상한: 0.2 × 1분 할인합 70 = 14 < 빨간불 30 (진입이 이득이 되지 않음)."""
from configs.js_nw7 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_far_red=0.2)
