"""r_h8 + 앞차 정지 기준 세 곳을 실제 범퍼 3.5 m로 정렬 (SUMO minGap 2.5 m 충돌 판정과 여유 1 m).
 - 보상 tg_s0_car 2.0→3.5, - 근거리 관측 필요 감속 기준 near_ref_m 2.0→3.5, - tg_box_keep_car(교차로 입구 목표로 바꿀 때 앞차도 후보).
11/23 r_h8 시드 200개 충돌 7건 중 4건이 minGap 판정(실제 2.2~2.4 m). r_h9는 보상만 바꿔 관측과 어긋나 악화(16/200)."""
from configs.r_h8 import SCENARIO as _S, REWARD as _R, HPARAMS  # noqa: F401
SCENARIO = dict(_S, near_ref_m=3.5)
REWARD = dict(_R, tg_s0_car=3.5, tg_box_keep_car=True)
