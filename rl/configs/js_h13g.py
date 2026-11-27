"""js_h13e(tg_far_scale 15) + tg_close_stop 1.0→0.5 (11/23 임재성). js_h13e 대비 한 변수.
js_h13f(tg_static_decel 2.0)는 앞차 6.93→7.57 m, 충돌 2→4로 악화. 서 있는 앞차 '가까움' 감점(최대 1.0/스텝)이
목표 안쪽 접근을 크게 막는지 본다. r_h5가 대기열 저속 추돌로 0.2→1.0 올린 값이라 중간값 0.5.
결과 (r_h13_25k에서 5만 학습, 3만 체크포인트 = models/js_h13g_30k.pt, 시드 2000–2999):
  r_h13 979/21, 정지선 6.61 m, 앞차 7.05 m → js_h13g 30k 969/31, 정지선 6.35 m, 앞차 4.80 m (5 m 이하 79%).
  측정: 정차 순간(0.5 m/s 이상에서 0.1 m/s 미만) 같은 차로 15 m 안 서 있는 앞차까지 범퍼 간격의 중앙값."""
from configs.js_h13e import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_close_stop=0.5)
