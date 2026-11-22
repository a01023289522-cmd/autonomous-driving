"""r_alley2 + 앞차 근거리 관측 2개(obs_near: 10 m 안 근접도, 앞차 2 m 뒤에 서려면 필요한 감속). 관측 43개.
docs/lessons.md 문제 1: 앞차 거리 입력(거리/50 m)으로는 0~5 m를 구분 못 해 대기열 저속 추돌·495951447 추돌.
기존 모델에 0 열을 붙여(rl/expand_obs.py) 시작하고, 1단계는 새 입력 열과 가치 머리만 학습(--new-cols 2, 팀원 local_b 방식)."""
from configs.r_alley2 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_near=True)
