"""밤 실험 A: r_scaled_foefix + 양보 위반 감점 2 (yield_penalty). 11/18 재생 분석: 위험 진입(우선 차량 TTC < 3초) 중 충돌 7%로
손익분기(약 8%)와 같아 양보를 배울 이유가 없었다. 충돌 여부와 상관없이 위험 진입마다 감점해 신호를 조밀하게 한다."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02, "idle_scaled": True, "yield_penalty": 2.0}
