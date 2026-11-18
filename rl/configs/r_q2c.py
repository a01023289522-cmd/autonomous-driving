"""r_q2 + 이어서 학습용 보수적 PPO 설정 + 차로 변경 감점 0.05 → 0.01.
- 학습률 1e-4 → 5e-5 (train_skku.py --lr-end 2.5e-5로 선형 감소), epoch 10 → 5, minibatch 64 → 128.
  11/18: 같은 학습 안에서도 체크포인트마다 충돌이 10–17%로 흔들렸다 (r_safe 25만 대 30만). GPT 교차검증도 같은 권고.
- 차로 변경 감점 0.01: 0.05는 정문 앞 일월로처럼 꼭 필요한 변경(2회)까지 막을 수 있다"""
from configs.r_q2 import SCENARIO  # noqa: F401
from configs.r_q2 import REWARD as _R
REWARD = dict(_R, lane_change_penalty=0.01)
HPARAMS = {"lr": 5e-5, "n_epochs": 5, "minibatch_size": 128}
