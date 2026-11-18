"""r_safe + 정차 감점 0.02 → 0.06. 재생 분석: 빨간불 정지 182회 중 140회가 정지선 20 m 넘게 앞(중앙값 47 m)에서 가속 명령
-0.7~-0.9로 확실하게 선다. 45 m에서 비례 감점이 스텝당 0.007뿐이라 약하다. 앞으로 붙게 하면 추돌이 늘 수 있어 시간 간격과 같이 본다."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.06, "idle_scaled": True, "yield_penalty": 2.0, "headway_s": 2.0}
