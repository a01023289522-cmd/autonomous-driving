"""r_s19 10만(시드 200개 94.0/3.5/2.5, 1200초면 96.5/3.5/0, 급제동 2.0/km, 495951447 충돌 1)에서 이어서 같은 보상으로 안정화.
이어서 학습할 때 체크포인트마다 완주가 86~96%로 흔들려서 학습률을 낮춘다 (5e-5 → 2e-5, --lr-end 1e-5)."""
from configs.r_s19 import SCENARIO, REWARD  # noqa: F401
HPARAMS = {"lr": 2e-5, "n_epochs": 5, "minibatch_size": 128}
