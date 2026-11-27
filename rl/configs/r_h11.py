"""r_h8 + tg_box_keep_car (교차로 입구 목표로 바꿀 때 앞차 목표도 함께 비교). 보상 버그 수정, r_h9·r_h10과 별도 후보.
11/23 r_h9 시드 1020(-5039133870#2): 다음 엣지 시작에 선 앞차 범퍼 2.6 m인데 목표는 엣지 끝 → 감점 0으로 다가가 minGap 판정."""
from configs.r_h8 import SCENARIO, REWARD as _R, HPARAMS  # noqa: F401
REWARD = dict(_R, tg_box_keep_car=True)
