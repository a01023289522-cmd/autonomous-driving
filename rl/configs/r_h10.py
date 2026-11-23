"""r_h8 + tg_far_scale 50→10 ('멀리 서 있음' 감점: 목표+band보다 5 m 더 멀면 스텝당 0.05 → 0.25). r_h9(tg_s0_car)와 별도 후보.
11/23 측정 r_h8 5만: 빨간불 정지선 앞 출력 0이 되는 가상 벽(앞차 칸) 거리 약 8 m = 앞차 뒤 정지 거리와 같음 → 정지선 6.5~8.4 m, 앞차 뒤 범퍼 7.7~10.8 m.
감점 0.04/스텝으로는 이 평형을 못 옮긴다. band(정지선 1~3 m, 앞차 2~3.5 m) 안은 여전히 0이라 바르게 선 대기에는 감점 없음(r_h3 빨간불 진입 원인 재발 방지)."""
from configs.r_h8 import SCENARIO, REWARD as _R, HPARAMS  # noqa: F401
REWARD = dict(_R, tg_far_scale=10.0)
