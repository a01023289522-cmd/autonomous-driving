"""처음부터 학습 두 번째 버전. 11/19 새벽: 처음부터 학습(r_q2_nojerk + --ppo-fix)이 위험 진입 5.4–5.7%, TTC 1초 미만 1–2회로
이어서 학습한 모델들(8–13%)보다 양보를 잘 배움. 같은 방향을 다른 설정으로 한 번 더 돌려 우연인지 확인한다.
- 보상: r_q2_nojerk에서 차로 변경 감점 0.05 → 0.01 (필요한 변경까지 막지 않게). 승차감 감점은 처음부터 학습(std 0.6)에서는
  탐색 노이즈를 벌하므로 뺀다
- 출발점: 정문 앞 일월로 추가 (정문 안쪽 교차로 양보 연습)
- PPO: GPT 교차검증의 처음부터 학습 권고 — 학습률 1e-4 → 3e-5(--lr-end), epoch 5, minibatch 128. --ppo-fix로 돌린다"""
from configs.r_q2_nojerk import SCENARIO as _S
from configs.r_q2_nojerk import REWARD as _R
SCENARIO = dict(_S, start_mix=["7754567510", "7754567510", "7755484380#0", "-5039133870#1", "3718967780#1", "5612296410"])
REWARD = dict(_R, lane_change_penalty=0.01)
HPARAMS = {"lr": 1e-4, "n_epochs": 5, "minibatch_size": 128}
