"""밤 실험 C: r_scaled_foefix + 정차 감점 0.02 → 0.06. 재생 분석: 빨간불 정지 68회 중 55회가 정지선 20 m 넘게 앞(중앙값 48 m),
그 자리에서 가속 명령 -0.7~-0.9로 확실하게 선다. 45 m에서 비례 감점이 스텝당 0.007뿐이라 약하다."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.06, "idle_scaled": True}
