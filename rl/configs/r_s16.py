"""r_s15 + 보수적인 앞차 붙어 서기: queue_approach를 SUMO 간격 3 m(앞범퍼 약 5.5 m) 이상, 1.5 m/s 이하에서만,
서 있는 앞차 앞 정차 감점 기준 3.5 (앞범퍼 약 6 m). r_s13(간격 0, 3 m/s)은 저속 추돌로 충돌 6~7/40."""
from configs.r_s15 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s15 import REWARD as _R
REWARD = dict(_R, queue_approach=True, queue_min_gap=3.0, queue_max_speed=1.5, idle_gap_queue=3.5)
