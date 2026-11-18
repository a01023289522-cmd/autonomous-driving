"""처음부터 학습 70만(100 에피소드 완주 93%, 충돌 6%, results/r_q2_nojerk_init_1119_003117/model_700k.pt)에서 이어서.
r_s2의 보상·출발점(차로 변경 감점 0.01, 정문 앞 일월로 출발) + 이어서 학습용 보수적 PPO(학습률 5e-5 → 2.5e-5, epoch 5,
minibatch 128). --ppo-fix. 남은 실패 7건 중 4건이 정문 안쪽 교차로(8577251160) 양보 실패."""
from configs.r_s2 import SCENARIO, REWARD  # noqa: F401
HPARAMS = {"lr": 5e-5, "n_epochs": 5, "minibatch_size": 128}
