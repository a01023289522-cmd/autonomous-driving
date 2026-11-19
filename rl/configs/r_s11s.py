"""r_s11 + 가까운 앞뒤 차 음수 거리(obs_close_signed). 495951447 저속 추돌 대책을 함께 넣은 비교용."""
from configs.r_s11 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_close_signed=True)
