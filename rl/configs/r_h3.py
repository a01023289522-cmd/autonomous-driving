"""r_h2 + tg_close_line 1.0: 빨간불 정지선에 지금 속도로 1 m 앞에 못 설 만큼 빠르게 다가가면 크게 감점 (앞차는 0.2 그대로).
11/23 r_h2 10만 시드 1022: 일월로 진입에서 빨간불 정지선 2 m 앞 3.2 m/s, 가속 +0.13 → 빨간불 진입·충돌 (감점 −0.04뿐)."""
from configs.r_h2 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_close_line=1.0)
