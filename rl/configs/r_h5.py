"""r_h4 + obs_red_wall: 빨간불 정지선을 정지선에 선 가상의 차로 앞차 칸에 (11/23)."""
from configs.r_h4 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_red_wall=True)
