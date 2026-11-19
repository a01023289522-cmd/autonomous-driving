"""확인용: r_s8 + queue_approach + idle_gap_queue 2.0 (갈래 비교로 간격 감점 수정 효과 확인)."""
from configs.r_s8 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s8 import REWARD as _R
REWARD = dict(_R, queue_approach=True, idle_gap_queue=2.0)
