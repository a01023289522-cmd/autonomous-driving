"""r_s8 10만(관측 41개, 시드 200개 95.0/2.5/2.5)에서 이어서. r_s11~r_s16에서 안전했던 개선만 얹는다:
빨간불 대기 감점 0.05 + 경로 중간 출발 투입 시각 0~90초 무작위. 진행 방향 관측(규정 소지, 실제로 거의 안 씀)과
앞차 붙어 서기(r_s16 시드 200개에서 495951447 충돌 9건)는 넣지 않는다."""
from configs.r_s8 import SCENARIO as _S, REWARD as _R, HPARAMS  # noqa: F401
SCENARIO = dict(_S, start_delay_max=90.0)
REWARD = dict(_R, red_wait_penalty=0.05)
