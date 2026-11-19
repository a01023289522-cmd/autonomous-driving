"""r_s5 + 정문 앞 일월로(5612296410) 출발 비중 확대. r_s5 10만(시드 200개 94.5/4.0/1.5)에서 이어서 학습.
11/19 r_s5 10만: 다른 신호는 정상 위치에 서는데 정문 앞만 20번 중 19번 멀리 섬(중앙값 40 m). 3차로 맨 왼쪽이라 '오른쪽 차로 있음' 반응이 가장 강한 곳.
r_s6의 정지선 감점 기준 2 m(idle_gap_tls)는 시드 40개 충돌 5–6건으로 나빠져서 쓰지 않는다."""
from configs.r_s5 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, start_mix=list(_S["start_mix"]) + ["5612296410"] * 3)
