"""r_idle_s500 + 교차 차량 관측 보완 (obs_foe_fix, 환경 v4). 11/18 충돌 분석: 연속 교차로 양보 정보 지연,
우선도로 직진 차 누락, 이미 지나간 차가 가장 가까운 차로 뽑힘. docs/experiments.md "교차 차량 관측 점검"."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02}
