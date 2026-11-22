"""r_g1을 '확실하게': 서 있는데 목표보다 멀면 감점이 10 m 초과에서 최대 0.3 (r_g1은 30 m에서 0.1), 가까움 감점 0.2.
11/22 사용자: 분명한 상황(서 있는 앞차·빨간불)에서 분명한 보상."""
from configs.r_g1 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_far=0.3, tg_far_scale=10.0, tg_close=0.2)
