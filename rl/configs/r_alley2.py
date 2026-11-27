"""r_alley + obs_first_foe: 양보 연결 앞에서 SUMO가 '내가 양보할 차'로 표시하지 않았어도 충돌 지점에 나보다 먼저 닿는 차를
양보 상대 칸에 넣는다 (11/22 플렁드 오거리 4493735400 충돌: 교차 차량이 3 m 앞인데 egoResponse=False라 관측에 없었음). 관측 개수 41 그대로."""
from configs.r_alley import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_first_foe=True)
