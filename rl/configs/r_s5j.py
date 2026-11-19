"""r_s5 + 승차감 감점(r_mix_q에서 맞춘 값: 0.5 × max(0, |가속 명령 변화량| − 0.7)²). 11/19 급가속 13.5회/km·급제동 3.0회/km.
이어서 학습이라 탐색 노이즈가 작아(std 약 0.30, 맞출 때 0.28) 처음부터 학습 때처럼 노이즈를 벌하는 문제가 작다. r_s5와 비교용."""
from configs.r_s5 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s5 import REWARD as _R
REWARD = dict(_R, jerk_penalty=0.5, jerk_deadzone=0.7)
