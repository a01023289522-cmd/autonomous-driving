"""평가 난이도: 특수 (회전교차로 혼잡). 기본 교통 + 회전교차로를 지나는 흐름 추가 (sumo/skku_map/scenarios.py rb_jam).
11/17 측정: 회전교차로 진입로 대기 평균 0.7대 → 3.7대. AV 입구 앞을 지나는 차는 시간당 약 200대로 거의 같음 (회전교차로 처리 용량 한계)."""
SCENARIO = {"extra_routes": ["scenario_rb_av.rou.xml", "scenario_rb_jam.rou.xml"]}
