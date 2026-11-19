"""r_q2에서 승차감 감점만 뺀 것. 승차감 감점의 효과·부작용 비교용이고, 처음부터 학습(std 0.6)에도 이것을 쓴다
(노이즈가 크면 승차감 감점이 탐색 노이즈를 벌하는 항이 된다)."""
from configs.r_q2 import SCENARIO  # noqa: F401
from configs.r_q2 import REWARD as _R
REWARD = dict(_R, jerk_penalty=0.0)
