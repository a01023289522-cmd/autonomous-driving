"""r_safe에서 양보 위반 감점만 2 → 5. 11/18 빠른 평가: r_safe 10만 스텝에서 시간 간격 위반은 1.6 → 0.1/1000스텝으로 줄었지만
위험 진입 비율은 8.5% → 8.4%로 그대로. 감점 크기가 모자란지 학습량이 모자란지 가른다."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02, "idle_scaled": True, "yield_penalty": 5.0, "headway_s": 2.0}
