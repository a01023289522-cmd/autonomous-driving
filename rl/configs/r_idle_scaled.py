"""r_idle_s500 + 정차 감점을 빈 공간에 비례하게 (idle_scaled). 11/18: 신호 대기 때 정지선 40–80 m 앞에 서는 문제.
계단형 감점은 조금 다가가도 줄지 않아서 다가갈 이유가 없었다."""
SCENARIO = {"train_seeds": list(range(500))}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02, "idle_scaled": True}
