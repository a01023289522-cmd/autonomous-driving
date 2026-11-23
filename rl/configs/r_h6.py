"""r_h5 + 양보 목표 강화. 11/23 r_h5 5만 시드 1075: 정문 8577251160에서 우선 차(5.4 m/s) 앞에 4.8 m/s로 진입 충돌.
양보 목표는 TTC 4초 미만에서야 켜지고(정지선 12 m), 가까움 감점이 0.2라 제동 −0.09뿐 (빨간불·서 있는 차는 1.0으로 고친 것과 같은 구멍).
tg_close_yield 1.0, tg_yield_ttc 6초(41 m 앞 우선 차부터 목표)."""
from configs.r_h5 import SCENARIO, REWARD as _R, HPARAMS  # noqa: F401
REWARD = dict(_R, tg_close_yield=1.0, tg_yield_ttc=6.0)
