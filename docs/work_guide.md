# 작업 가이드 — AV 학습·평가·데이터 수집

팀원 각자 바로 작업을 시작하기 위한 문서. 도로 구조는 컨설팅 피드백 후 확정하므로, **지금은 임시 경로로 학습 흐름을 만든다.**

---

## 1. 이 프로젝트에서 우리가 하는 일

주행 로직을 직접 쓰지 않는다. **시험장과 채점표를 만들고, 신경망이 시행착오로 운전을 배운다.**

| | 우리가 정하는 값 | 학습이 자동으로 바꾸는 값 |
|---|---|---|
| 무엇 | 보상 점수, `gamma`, 관측 항목 | 신경망 가중치 (약 7만 개 이상) |
| 의미 | 무엇을 잘한 걸로 칠지 | 실제 주행 로직 |
| 위치 | `rl/configs/*.py` | `results/*/model.pt` |

반복 작업: **변수 하나 변경 → 학습 → 주행을 직접 봄 → 100 에피소드 평가 → 기록표 작성**

## 2. 처음 설정 (한 번만)

1. SUMO 1.27.1 설치 ([sumo/README.md](../sumo/README.md))
2. 이 저장소 옆에 수업 저장소를 clone (폴더 이름 그대로). 다른 곳에 두면 환경변수 `COURSE_REPO`에 경로 지정
   ```
   상위폴더/
     autonomous-driving/                  ← 이 저장소
     Artificial-Intelligence-and-Control-for-Autonomous-Driving/   ← 수업 저장소
   ```
3. 수업 저장소 안내대로 Python 패키지(`torch`, `gymnasium` 등) 설치
4. 확인 (이 저장소 최상위에서 실행):
   ```
   python -X utf8 rl/train_skku.py --config example --timesteps 2048
   ```

## 3. 명령어

모두 이 저장소 최상위에서 실행한다. Windows에서 한글이 깨지면 `-X utf8`을 붙인다.

| 할 일 | 명령 |
|---|---|
| 학습 | `python -X utf8 rl/train_skku.py --config 내설정` |
| 학습 곡선 | `tensorboard --logdir results` |
| 주행 보기 | `python -X utf8 rl/test_skku.py results/.../model.pt --config 내설정 --episodes 3` |
| 100 에피소드 평가 | `python -X utf8 rl/test_skku.py results/.../model.pt --config 내설정 --episodes 100 --nogui` |
| 데이터 수집 | `python -X utf8 rl/collect_skku.py --config 내설정 --model results/.../model.pt --episodes 100` |
| BC 학습 | 수업 저장소에서 `python train_bc.py --data <수집한 npz>` |
| 칼럼 과제용 CSV | `python -X utf8 rl/make_column_sample.py 출력.csv` (도착·충돌·차로 변경이 들어간 16줄) |
| 도로만 보기 | `sumo/skku_map`에서 `python -X utf8 view_av_route.py` (기본 승용차가 경로 주행. 학습한 AV 아님) |

**실험 설정 만들기:** `rl/configs/example.py`를 복사해 `rl/configs/보상_01.py`처럼 저장하고, 바꿀 값만 적는다. `base.py`는 고치지 않는다.

```python
TOTAL_TIMESTEPS = 50_000
REWARD = {"collision_penalty": 20.0}
HPARAMS = {"gamma": 0.995}
```

**알아 둘 시간** (측정값)
- 주행은 초당 약 25~40스텝, 에피소드 시작에 약 4초. 20만 스텝은 대략 몇 시간 걸린다. 후보는 5만 스텝으로 먼저 거른다.
- 시드별 첫 시작만 약 26초 걸린다 (배경 교통 10분을 채워 `sumo/skku_map/work/states/`에 저장). 평가 시드 100개는 처음 한 번 약 45분.
- 도로·교통 파일이 바뀌면 저장 상태는 자동으로 다시 만들어진다.
- 데이터는 1스텝당 약 12 KB(압축). 100 에피소드면 약 2 GB 예상이라, 저장 범위를 줄여야 한다 (역할 B).

## 4. 코드 구조

| 파일 | 내용 |
|---|---|
| `rl/skku_env.py` | 수업 환경을 우리 도로에 연결 (경로, 시드, 교차로 충돌 검사, 배경 교통 저장·불러오기) |
| `rl/configs/` | 실험 설정 |
| `rl/train_skku.py` | PPO 학습 |
| `rl/test_skku.py` | 고정 시드 평가 |
| `rl/collect_skku.py` | 데이터 수집 |
| `sumo/skku_map/` | 도로망·교통 |
| 수업 저장소 `env/sumo_env.py` | 관측(31개), 행동, 보상 계산 |
| 수업 저장소 `algorithms/ppo.py` | PPO 본체 |

**임시 AV 경로:** 서부로 남행(사거리 약 300 m 앞) → 성대역 사거리 → 버스 구간 → 올리브영 사거리 → 오거리 3곳 → 회전교차로 → 서부로×일월로 → 정문 → L1 주차장 통로. 약 2.8 km, 엣지 34개. `rl/configs/base.py`의 `start_edge`, `goal_edge`로 바꾼다.

## 5. 역할 분담

담당자는 회의에서 정한다.

### 1단계: 기반 작업 (이번 주)

| 역할 | 할 일 | 파일 | 담당 |
|---|---|---|---|
| A 환경 | 아래 6장 1~4번 | `rl/skku_env.py` | |
| B 평가·데이터 | 평가 지표 추가(회전교차로 진입 시 주변 차 수), 수집에 신호 상태·차량 종류 추가, 저장 범위 축소 | `rl/test_skku.py`, `rl/collect_skku.py` | |
| C 기준선 | SUMO 기본 주행 정책을 평가·수집에 추가 (비교 기준이자 BC용 데이터) | `rl/collect_skku.py` | |
| D 정리 | 신호 위반 벌점 등 보상 초안, 실험 기록표 관리, 프로젝트 페이지 뼈대 | `docs/experiments.md` | |

환경 코드(`rl/skku_env.py`)는 **A만 수정**한다. 바꾸면 기록표에 환경 버전을 적어 알린다.

### 2단계: Trial (환경 완성 후)

| Trial | 조정 변수 | 주요 구간 | 주로 볼 시점 (출발 후) | 볼 것 |
|---|---|---|---|---|
| 1 보상 | `REWARD`: `collision_penalty`, `speed_weight`, `arrival_bonus`, `blocked_penalty`, 신호 벌점 | 성대역 사거리, 버스 구간 | 0~160초 | 충돌 지점, 신호 대기, 버스 뒤 대기·추월 |
| 2 관측·시야 | `OBSERVATION["visibility"]`, `HPARAMS["gamma"]`, 신호·교차 차량 입력 유무 | 오거리 3곳, 회전교차로 | 160~230초 | 진입 시점 판단, 양보 여부 |
| 3 모방 학습 | `train_bc.py`의 `--lr`, `--epochs`, 데이터 양, BC 결과를 PPO 시작값으로 | 전 구간, 특히 서부로×일월로 | 230~395초 | 기준선을 얼마나 따라 하는지 |
| 4 다른 방식 | SAC 등 알고리즘, 쉬운 교통부터 올리는 단계별 학습 (`traffic.py`의 `DEMAND`) | 정문, L1 주차장 | 395~475초 | 완주율, 좌회전 진입 |

시점은 기본 승용차로 잰 중앙값이다. 학습한 AV는 달라질 수 있다.

**증상별로 바꿀 변수**

| 관찰 | 변수 |
|---|---|
| 충돌이 많음 | `collision_penalty` 올리기, `close_gap_penalty` 올리기 |
| 서 있기만 함, 시간 초과 | `speed_weight` 올리기, `collision_penalty` 내리기 |
| 빨간불 통과 | 신호 벌점 추가·올리기 |
| 차로를 안 바꿈 | `lane_entropy_coef` 올리기, `lane_keep_bias` 내리기 |
| 회전 전에 차로를 못 맞춤 | `visibility` 늘리기, 경로 기준 차로 입력 점검 |
| 도착에 무관심 | `gamma` 올리기, `arrival_bonus` 올리기 |
| 보상 그래프 요동 | `lr` 내리기 |

## 6. 환경에 남은 작업 (역할 A)

지금은 AV가 우리 도로를 달리기만 한다. **아래를 끝내야 학습 결과를 믿을 수 있다.**

1. **신호 관측:** 관측에 다음 신호 색과 거리를 추가 (`_get_obs`, `obs_dim`). 지금 AV는 신호를 모른다.
2. **경로 기준 차로 정보:** 수업 코드의 연결성은 "어디로든 이어지면 1"이라, 다음 회전에 필요한 차로를 모른다.
3. **교차 차량 관측:** 오거리·회전교차로에서 옆에서 오는 차를 못 본다.
4. **안전 제어 방침:** 수업 환경은 `speedMode=0`으로 SUMO 안전 제어를 모두 끈다. 신호·교차로 우선권을 SUMO에 맡길지 정책이 배울지 결정 (`userdoc/TraCI/Change_Vehicle_State.html`).
5. **제한속도:** `vmax`가 시속 50 km 고정이라 교내(시속 20 km)에서도 위반이 가능하다.

## 7. 지켜야 할 규칙

1. 같은 환경 버전으로 비교한다.
2. 평가는 `test_skku.py`로만 한다 (고정 시드 100개).
3. 한 번에 변수 하나만 바꾼다.
4. 실패도 [실험 기록표](experiments.md)에 적는다. 최종발표의 "문제 해결 과정" 자료가 된다.
5. 자기 설정은 `rl/configs/`에 파일로 올린다. `results/`와 `data/`는 올리지 않는다.

## 8. 피드백 후 결정할 것

- 경로 범위, 학교 오른쪽 도로 삭제
- 고속도로 포함 여부, 유령 체증 실험
- 데이터 컬럼 범위, 샘플 수 (조교 공지 확인)

**컨설팅 11/17, 11/24 / 최종발표 11/28.** 평가 기준은 수업 저장소 `project_materials/6_Project_Evaluation.md`.
