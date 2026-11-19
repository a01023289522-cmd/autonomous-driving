"""r_s8 + 가까운 앞뒤 차 거리를 음수로 그대로(obs_close_signed). r_s8 10만(시드 40개 38/0/2)에서 이어서 학습.
11/19 r_s9 15만 재생: obs_close_fix가 2.5 m 안을 전부 0으로 고정해 다가가는 동안 관측이 안 변하고 AV가 시속 3~4 km로 닿음.
교차로 안 관측(obs_inside_fix)은 r_s9에서 495951447 충돌이 늘어 이번에는 넣지 않는다 (따로 확인)."""
from configs.r_s8 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_close_signed=True)
