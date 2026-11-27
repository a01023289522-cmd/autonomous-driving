"""r_h4 + obs_red_wall(빨간불 정지선을 정지선에 선 가상의 차로 앞차 칸에) + tg_close_stop 1.0(서 있는 앞차에 너무 가까우면 크게).
11/23: 학습 없이 obs_red_wall만으로 일월로 진입 빨간불 53번 모두 정지. 대신 사거리 진입로 대기열 저속 추돌 2건(감점 약함)."""
from configs.r_h4 import SCENARIO as _S, REWARD as _R, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_red_wall=True)
REWARD = dict(_R, tg_close_stop=1.0)
