"""js_nw2 + tg_far_red 0 (11/24 임재성). 빨간불 벌점 10에서 '멀리 섬' 감점을 빨간불 정지선에만 끈다. 변수 1개 (비교 대상 js_nw2, js_nw4와 2×2)."""
from configs.js_nw2 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_far_red=0.0)
