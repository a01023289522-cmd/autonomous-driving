"""r_mix_q + 대기열 수정(queue_fix) + 정차 기준 15 → 8 m (idle_gap).
11/18 측정(r_idle_scaled 5 시드): AV와 앞차가 둘 다 서 있던 1045스텝 모두 간격 15 m 이상, 중앙값 41 m. 수업 코드 막힘 감점(앞차 20 m 안)과
6 m 간격 감점(정상 대기 간격 2.5 m에서 80초 대기 −16 > 충돌 −5)이 대기열에 붙는 것을 벌하고 정차 감점이 앞으로 밀어 약 40 m에서 균형.
queue_fix: 앞차(정류장 버스 포함)가 서 있으면 막힘 감점, 둘 다 서 있으면 6 m 간격 감점을 되돌림. 달리는 중은 그대로.
idle_gap 8 m: 대기열에서 앞차 8 m, 정지선 8 m 안까지 다가가야 정차 감점이 없다."""
from configs.r_mix_q import SCENARIO  # noqa: F401
from configs.r_mix_q import REWARD as _R
REWARD = dict(_R, queue_fix=True, idle_gap=8.0)
