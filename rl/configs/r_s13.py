"""r_s11s + 서 있는 앞차에 붙어 서기: queue_approach(세울 수 있는 속도로 다가가는 동안 6 m 간격 감점 되돌림) + idle_gap_queue 2.0
(서 있는 앞차 앞 정차 감점 기준 8 → 2, SUMO 간격 기준 = 앞범퍼 약 4.5 m). 11/19 측정: 서 있는 앞차 뒤 정지 간격 중앙값 약 16 m,
다가가면 간격 감점 때문에 할인합이 오히려 낮음(시드 1003: −0.68 대 +0.18)."""
from configs.r_s11s import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s11s import REWARD as _R
REWARD = dict(_R, queue_approach=True, idle_gap_queue=2.0)
