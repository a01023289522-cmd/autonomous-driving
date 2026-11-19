"""r_s11s 15만(시드 40개 38/1/1, 급제동 1.8/km)에서 이어서. 정문 앞 멀리 정차 대책 강화.
11/19 갈래 비교(r_s11s 15만, 시드 8개): 정지선까지 다가가면 8개 모두 이득(+0.14~+1.0, 평균 약 +0.6)인데 정책은 안 바뀜.
추정: 이득이 약 25스텝에 나뉘어 스텝당 advantage가 +0.03 수준이라 잡음에 묻힘. 빨간불 대기 감점(앞이 정지선까지 빈 경우만)을
0.05 → 0.2로 올리고 정문 앞 출발 비중을 늘린다. 앞차·교차로가 있는 상황에는 붙지 않는 항이라 충돌 쪽 부작용이 적을 것으로 본다."""
from configs.r_s11s import SCENARIO as _S, REWARD as _R, HPARAMS  # noqa: F401
SCENARIO = dict(_S, start_mix=list(_S["start_mix"]) + ["5612296410"] * 3)
REWARD = dict(_R, red_wait_penalty=0.2)
