"""r_s8(아주 가까운 앞뒤 차 관측 수정) + 교차로 안 교차 차량 관측(obs_inside_fix). r_s5 10만에서 이어서 학습.
11/19 실패 재생: 율전로98번길 좌회전 495951808 충돌(시드 1110, 1174) — 양보 연결로 교차로에 들어선 직후 관측이 다음 교차로 기준
('양보 0, 교차 차량 없음')으로 바뀌고, 지금 교차로 안에서 교차하는 차가 getJunctionFoes에 안 나와 AV가 가속. 관측 개수 그대로(41)."""
from configs.r_s8 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_inside_fix=True)
