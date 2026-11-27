"""js_nw7 + yield_penalty 2 → 6 (11/25 임재성). nw7 10만 시드 1000–1199 충돌 5건 중 4건이 무신호 좌회전 495951808.
빨간불 벌점을 30으로 올린 뒤 양보 위반(2)은 상대적으로 너무 작음. js_nw7_100k에서 이어 학습."""
from configs.js_nw7 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, yield_penalty=6.0)
