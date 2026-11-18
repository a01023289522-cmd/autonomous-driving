"""r_idle_scaled(11/18 최고, 충돌 13%)에서 이어서 관측 보완(obs_foe_fix)만 켠다. 남은 충돌 중 14·11번 엣지 5건이 관측 구멍 위치."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02, "idle_scaled": True}
