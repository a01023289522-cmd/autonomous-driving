"""회전교차로 단계 학습 1단계: r_idle_s500 보상 + 회전교차로 혼잡 교통(level_special). 11/18 v3 평가에서 충돌의 절반 이상이
회전교차로 진입 양보 실패. 혼잡한 회전교차로를 더 자주 겪게 한 뒤 2단계에서 기본 교통(r_idle_s500)으로 돌아온다."""
SCENARIO = {"train_seeds": list(range(500)), "extra_routes": ["scenario_rb_av.rou.xml", "scenario_rb_jam.rou.xml"]}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02}
