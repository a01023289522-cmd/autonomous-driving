"""r_s8 + 앞차 근거리 관측(obs_near: 10 m 안 근접도·필요 감속) — 새 입력 열만 학습률 5e-4로 (11/22, 골목 r_alley3b와 같은 방법, 원래 지도 + G1 신호 제거)."""
from configs.r_s8 import SCENARIO as _S, REWARD, HPARAMS as _H  # noqa: F401
SCENARIO = dict(_S, obs_near=True)
HPARAMS = dict(_H, lr=5e-4)
