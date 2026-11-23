"""r_h11 + tg_yield_internal (앞 교차로 안에서부터 다음 교차로 양보 목표). 관측·보상 크기·충돌 판정은 그대로.
11/23 r_h11 5만 시드 2000–2999 충돌 40건 중 495951808 18건: 양보 목표가 앞 교차로 4637441266 안에서 꺼져 있어 진입로(10.4 m) 9 m 앞에서야 켜짐."""
from configs.r_h11 import SCENARIO, REWARD as _R, HPARAMS  # noqa: F401
REWARD = dict(_R, tg_yield_internal=True)
