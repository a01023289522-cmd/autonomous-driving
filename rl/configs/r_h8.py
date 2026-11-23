"""r_h7 + obs_tls_left_fixed (신호 남은 시간 칸 고정, 빨강·노랑 표시 유지). 보상·다른 관측 변경 없음.
11/23 r_h7 10만 시드 1164: 남은 시간 30→5.5초 순간 서 있는 버스 23 m 앞에서 가속, 이 칸만 되돌리면 감속. 기준선은 r_h7 10만."""
from configs.r_h7 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_tls_left_fixed=True)
