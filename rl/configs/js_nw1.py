"""js_h13e - obs_red_wall (11/24 2차 컨설팅: 빨간불 정지선을 가상 정지 차량으로 앞차 칸에 넣는 관측 가공 금지). 다른 관측·보상 그대로.
빨간불 정지 목표(target_gap 'red')는 보상 쪽에 이미 있어 관측만 끈다."""
from configs.js_h13e import SCENARIO as _S, HPARAMS, REWARD  # noqa: F401
SCENARIO = dict(_S, obs_red_wall=False)
