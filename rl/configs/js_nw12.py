"""js_nw7 + yield_ttc 4 → 6 (11/25 임재성). 무신호 좌회전(495951808) 충돌: 우선 차량이 6초 안에 오면 진입을 양보 위반으로 본다."""
from configs.js_nw7 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, yield_ttc=6.0)
