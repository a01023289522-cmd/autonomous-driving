"""r_alley2를 30만(시드 1200–1599 95.25/4.25, 1600–1799 91.5/7.0)에서 학습률 절반으로 이어서. 남은 실패는 플렁드 오거리 판단
(양보 상대가 충돌 지점에 있는데 시속 13 km로 진입, 반대 방향 차가 골목 안인데 교차로에 들어가 멈춤)과 495951447. 관측에는 정보가 있음."""
from configs.r_alley2 import SCENARIO, REWARD  # noqa: F401
from configs.r_alley2 import HPARAMS as _H
HPARAMS = dict(_H, lr=2.5e-5)
