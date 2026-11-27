"""r_h8 + tg_s0_car 2.0→3.5 (서 있는 앞차 뒤 목표를 실제 범퍼 간격 3.5 m로, band 1.5 → 허용 3.5~5 m).
11/23 확인: SUMO는 범퍼 간격 < minGap 2.5 m면 충돌로 기록(userdoc/Simulation/Safety.html, collisionMinGapFactor 1.0).
보상 gap = getLeader 거리 + minGap = 실제 범퍼 간격인데 목표가 2.0 m라 2.0~2.5 m(감점 0 구간)가 충돌 판정 구간.
r_h8 5만 시드 200개 충돌 7건 중 4건이 이 유형(0.5~0.9 m/s로 서 있는 앞차에 다가가다 실제 간격 2.2~2.4 m에서 기록). 나머지 3건 495951808 교차로는 별개."""
from configs.r_h8 import SCENARIO, REWARD as _R, HPARAMS  # noqa: F401
REWARD = dict(_R, tg_s0_car=3.5)
