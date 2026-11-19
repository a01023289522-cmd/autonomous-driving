"""r_q2c + 앞차 TTC 감점 (TTC 3초 미만이면 0.2 × (3 − TTC)/3). r_q2c와 이것 하나만 다르다.
11/18: r_q2 10만 스텝 충돌 8/20 중 6건이 출발 직후 첫 초록불에서 회전하며 느려지는 앞차를 감속 없이 추돌.
TTC<3초는 정상 주행 스텝의 0.57%뿐이고 충돌 장면에서는 약 3초 전부터 이어진다 (측정). GPT 교차검증도 같은 결론."""
from configs.r_q2c import SCENARIO, HPARAMS  # noqa: F401
from configs.r_q2c import REWARD as _R
REWARD = dict(_R, ttc_penalty=0.2, ttc_s=3.0)
