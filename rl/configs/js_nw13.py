"""js_nw7 + yield_near_m 5 → 10 (11/25 임재성). 충돌 지점 10 m 안의 우선 차량은 서 있어도 위험(0초)으로 본다."""
from configs.js_nw7 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, yield_near_m=10.0)
