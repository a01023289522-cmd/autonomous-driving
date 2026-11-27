"""js_nw7 + collision_penalty 5 → 15 (11/25 임재성). 빨간불 30 대비 충돌 5가 6배 작아 '충돌보다 신호가 더 중요'한 상태. js_nw7_100k에서 이어 학습."""
from configs.js_nw7 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, collision_penalty=15.0)
