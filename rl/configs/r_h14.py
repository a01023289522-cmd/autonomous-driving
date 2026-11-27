"""r_h11 + obs_merge_lead (교차로 안 합류 차를 앞차로: 관측 앞차 칸·근거리 칸과 목표 간격 보상이 같은 차). r_h13과 별도 후보.
11/23 r_h11 5만 시드 2000–2999 495951447 충돌 4건 중 3건(2021·2355·2360): getLeader가 옆 내부 차로 합류 차를 놓친 순간 출발 + 먼 앞차 '멀리' 감점으로 찔끔 전진."""
from configs.r_h11 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_merge_lead=True)
