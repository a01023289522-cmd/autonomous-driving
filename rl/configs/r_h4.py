"""r_h3 + 허용 구간: 정지선 1~3 m(tg_band_line 2), 앞차 2~3.5 m(tg_band_car 1.5) 안에 서 있으면 '멀리 섬' 감점 0.
11/23 측정: r_h3 50k 일월로 진입 빨간불 — 3.7 m에 서 있어도 스텝당 −0.03, 98초 대기 합 −5.5 > 빨간불 진입 −5 → 출발해 진입."""
from configs.r_h3 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_band_line=2.0, tg_band_car=1.5)
