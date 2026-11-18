"""r_idle_s500 + 양보 위반 감점 (yield_penalty). 양보해야 하는 연결에 우선 차량이 3초 안에 오는데 들어가면 1회 감점.
11/18 임재성: 충돌 감점 크기만으로는 양보 실패가 안 줄어듦 → 충돌하지 않아도 위험한 진입에 감점을 준다.
관측 보완(obs_foe_fix)을 같이 켠다: 우선 차량이 관측에 보여야 양보를 배울 수 있다. 비교 기준은 r_foefix."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02, "yield_penalty": 2.0}
