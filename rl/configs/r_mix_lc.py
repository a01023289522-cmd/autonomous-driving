"""r_safe_mix + 차로 변경 감점 0.05 (수업 코드의 lane_change_penalty, 기본 0). 11/18: 출발점 섞기로 위험 진입 8.5% → 3.2%,
TTC 1초 미만 0건이 됐지만 학습 중 차로 변경이 늘어 서부로(5552317710#2) 왼쪽 차로 끝에 서는 시간초과가 생겼다(10만 스텝 15/20).
관측의 차로 연결성은 경로 기준이 아니라서(어디로든 이어지면 1) AV는 지금 차로가 경로로 가는지 모른다. 필요 없는 변경을 줄인다."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True,
            "start_mix": ["7754567510", "7754567510", "7755484380#0", "-5039133870#1", "3718967780#1"]}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02, "idle_scaled": True, "yield_penalty": 2.0, "headway_s": 2.0,
          "lane_change_penalty": 0.05}
