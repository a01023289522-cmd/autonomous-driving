"""목표 간격 하나로 앞차·빨간불·양보를 다룬다 (r_tg4와 같은 값, 원래 지도). r_n1에서 이어서.
6 m·2초 근접 감점, 빨간불 접근 보상은 끈다. 서 있는 대상의 목표 = 2 m(앞차)·1 m(정지선) + v²/(2·2.5).
가까우면 tg_close 0.1 비례, 거의 서 있는데(1 m/s 미만) 목표보다 멀면 tg_far 0.1 × (초과/30 m)."""
from configs.r_n1 import SCENARIO as _S, REWARD as _R, HPARAMS as _H  # noqa: F401
SCENARIO = dict(_S, obs_tls_foe=True,   # 빨간불·노란불이면 교차 차량 칸 비움 (정문 멀리 정지 원인)
                obs_inside_fix=True)  # 양보 연결로 들어선 교차로 안의 교차 차량도 계속 관측 (정문 안쪽 8577251160 충돌: 들어서면 양보 0·교차 차량 없음 → 가속)
REWARD = dict(_R, target_gap=True, tg_close=0.1, tg_far=0.1, tg_static_decel=2.5, tg_range=100.0, tg_far_speed=1.0,
              close_gap_penalty=0.0, headway_s=0.0, red_approach=0.0)
HPARAMS = dict(_H, lr=5e-5)
