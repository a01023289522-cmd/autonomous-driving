"""r_idle + 학습 교통 시드 20 → 500개. 11/18 충돌 분석: 양보 실패 12건은 상대 차가 관측에 있었는데도 진입했다.
학습 시드 20개로는 평가 시드의 다양한 양보 상황을 덜 겪는다 (20 에피소드 충돌 5% → 100 에피소드 20%)."""
SCENARIO = {"train_seeds": list(range(500))}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02}
