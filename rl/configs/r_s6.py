"""r_s5 + 정지선 앞 정차 감점 기준 2 m (idle_gap_tls). r_s5 10만(정지선까지 중앙값 8.5 m)에서 이어서 학습.
idle_gap 8 m는 앞차 간격 기준이라 그대로 둔다. 빨간불 접근 보상(red_approach 1.0)과 신호 위반 감점(−5)도 그대로."""
from configs.r_s5 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s5 import REWARD as _R
REWARD = dict(_R, idle_gap_tls=2.0)
