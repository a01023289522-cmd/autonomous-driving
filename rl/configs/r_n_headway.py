"""밤 실험 B: r_scaled_foefix + 앞차 시간 간격 2초 (headway_s). 출발 직후 추돌 4건: 6 m 고정 기준은 시속 20 km 접근에 늦다.
재생 분석: 정상 주행에서 새로 감점되는 스텝 0.9%."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02, "idle_scaled": True, "headway_s": 2.0}
