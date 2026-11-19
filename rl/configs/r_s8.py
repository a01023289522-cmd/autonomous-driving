"""r_s5 + 아주 가까운 앞뒤 차 관측 수정(obs_close_fix). r_s5 10만(시드 200개 94.5/4.0/1.5)에서 이어서 학습.
11/19 실패 재생: 교차로 495951447 충돌 4건(시드 1020, 1059, 1077, 1172) 모두 합류 차에 다가가다 거리가 minGap보다 작아지는 순간
수업 관측이 '앞차 없음'으로 바뀌어 AV가 가속한 추돌. 관측 개수는 그대로(41)라 이어서 학습 가능."""
from configs.r_s5 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_close_fix=True)
