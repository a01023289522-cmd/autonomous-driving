# 프로젝트 개요

수업 자료(`0_Project_Introduction.md`, `5_Project_Preparation.md`)를 팀 진행용으로 요약한 문서.
원문은 [수업 저장소의 project_materials](https://github.com/bmil-ssu/Artificial-Intelligence-and-Control-for-Autonomous-Driving/tree/main/project_materials)에서 확인한다.
수업 자료가 바뀌면 이 요약도 함께 고친다.

---

## 1. 주제

> **대한민국의 실제 도로 구조를 SUMO 환경에 구현하고, 그 도로에서 주행하는 자율주행 차량의 의사결정 모델을 구축한다.**

- 실제 도로와 **1:1로 똑같을 필요는 없다.** 차로 수, 교차로 형태, 진입·진출 방향, 회전 구조, 차선 연결을 자연스럽게 반영하면 된다.
- 단순 직선보다 **차량끼리 상호작용이 생기는 구조**를 권장한다.
  - 예: 삼거리, 사거리, 오거리, 로터리(회전교차로), 합류, 분기, 차로 감소, 복합·비정형 교차로
  - 수업 예시: 광화문, 팔달문(로터리 + 삼거리), 숭례문 인근 오거리
  - 그 외 자유: 강남역, 행궁동, 성대 앞, 수원역, 홍대입구 등
- 어떤 "한국다운" 요소를 넣을지는 [한국 도로의 특징](korean_road_features.md) 참고

## 2. 최종 결과물

- 한국 실제 도로를 반영한 **SUMO 환경**
- 자연스럽게 주행하는 **일반 차량(HV)** — Krauss / IDM / EIDM / ACC 4종을 섞어서 투입
- 자율주행 차량(AV)의 **관측(Observation) / 행동(Action) / 보상(Reward)** 정의
- 강화학습(PPO) 또는 모방학습(BC)으로 **학습된 AV 모델**
- 학습 모델로 수집한 **주행 데이터셋** `(state, action, reward, next_state, done)`
- (선택) 데이터 기반 학습: BC 또는 Offline RL
- **제출물**: 프로젝트 페이지, 코드(GitHub), 발표자료, 주행 데이터(Hugging Face) — [평가 기준 6절](evaluation.md#6-최종-제출물)

## 3. 평가 기준

> **최신·상세 기준은 [평가 기준과 발표 일정](evaluation.md)을 따른다.** (수업 6장, 2026-10-25)
> 아래는 수업 0장의 초기 기준이다. 6장에서 충돌률 기준이 **< 5%** 로 정리되었다.

| 항목 | 내용 |
|---|---|
| **도로 구조 구현** (가장 중요) | 실제 한국 도로의 특징을 잘 반영했는가 |
| 도로 구조의 복잡성 / 완성도 | 교차로, 차선, 합류, 분기 등 의미 있는 구조가 있는가 |
| **Simulation 안정성** (중요) | 비정상적인 정체·오류 없이 정상 주행하는가 |
| 일반 차량 구성 | IDM 등 일반 차량 controller가 정상 주행하는가 |
| **Collision Rate** | 최종 AV 충돌률 **≤ 5%** |
| Dataset 구축 | State / Action / Reward가 정상 저장되었는가 |
| Option | 추가 알고리즘, 환경 개선, 분석 |
| 완성도 | 프로젝트 페이지, HuggingFace 업로드, 보고서 |

정성 평가(다른 팀이 평가할 수 있음): 실제 도로처럼 보이는가, 구조가 흥미로운가, 상호작용이 충분한가, 난이도가 적절한가, 안정적인가, 자율주행 문제로 의미가 있는가.

> 복잡한 알고리즘을 구현했는지는 평가의 중심이 아니다. **수업 제공 알고리즘으로 충분하다.**

## 4. 진행 단계 (수업 권장 순서)

```text
 1. 실제 도로 조사와 단순화 범위 결정
 2. Node / Edge / Lane / Connection 구현
 3. 모든 Route 단독 주행 확인
 4. 일반 차량 교통 흐름 확인
 5. ego(AV) 생성과 목적지 도착 확인
 6. Observation 값 확인
 7. Action 적용 확인
 8. Reward와 종료 조건 확인
 9. 작은 규모 학습
10. 본 학습과 하이퍼파라미터 비교
11. 100 Episode 이상 최종 평가
12. 데이터셋·영상·보고서 정리
```

> **도로와 환경이 완성되기 전에 긴 학습을 시작하지 않는다.** 환경 오류는 학습 시간을 늘려도 해결되지 않는다.

## 5. 수업 코드 구조 (작업할 때 참고)

수업 코드는 세 층으로 나뉜다. 위층을 바꾸면 아래층도 확인해야 한다.

```text
도로 & 교통        env/road_config.py + env/road_builder.py   (env/sumo/ 는 자동 생성)
      ↓
주행 환경          env/mdp_config.py + env/sumo_env.py         (관측·행동·보상, TraCI 제어)
      ↓
학습 & 평가        train.py, train_bc.py, algorithms/, test.py, collect_pomdp_data.py
```

| 바꾸고 싶은 것 | 먼저 볼 파일 | 더 고쳐야 할 때 |
|---|---|---|
| 도로 길이·차선 수·제한속도 | `env/road_config.py` | 복잡한 형상은 `env/road_builder.py` |
| 교차로·합류·분기·회전교차로 | `env/road_builder.py` | 연결에 따라 `env/sumo_env.py` |
| 일반 차량 종류·비율·속도·교통량 | `env/road_config.py` | 새 Route/Flow는 `env/road_builder.py` |
| AV 출발 위치·차선·속도 | `env/road_config.py` | 여러 출발점은 `env/sumo_env.py` |
| 관측 범위·항목 | `env/mdp_config.py` | 항목 추가는 `env/sumo_env.py`의 `_get_obs()` |
| 보상·종료 조건 | `env/mdp_config.py`, `train.py` | 계산 방식은 `env/sumo_env.py`의 `step()` |
| PPO 설정 | `train.py` (`HPARAMS`) | 구조 변경은 `utils/networks.py` |

### 도로 구현 방식 (팀이 정해야 함)
- **방식 A — `road_builder.py` 확장**: Python으로 노드·엣지·Route를 생성. 반복 실험과 공유가 쉽다.
- **방식 B — netedit / 외부 도로 파일 사용**: 복잡한 교차로를 화면에서 편집하기 쉽다. 단, `road_builder.py`가 완성 파일을 덮어쓰지 않게 실행 구조를 바꿔야 하고, 완성 파일을 저장소에 포함해야 한다.
- 어느 방식이든 **팀원·조교가 저장소를 새로 받아 같은 환경을 재현할 수 있어야 한다.**

### 도로를 바꿀 때 꼭 확인할 것 (`env/sumo_env.py`의 직선 도로 전제)
- AV와 일반 차량이 쓰는 **Route 이름**(현재 `r0` 하나)
- **도착 판정** 위치, 도로 전체 길이를 이용한 완주 판정
- 일반 차량 사전 배치(prefill)가 "엣지 하나"를 전제로 위치를 계산하는 부분
- 신호등·경로 선택이 있으면 **현재 관측(31차원)과 행동만으로 충분한지** 검토
  (신호 상태, 정지선까지 거리, 진행 방향, 다음 Edge 등)

### 자주 쓰는 실행 명령 (수업 코드 폴더에서)
```bash
python view_road.py                       # 도로 + 일반 차량 GUI 확인 (▶ 눌러 재생)
python view_road.py --netedit             # 도로 구조만 편집기로 보기
python view_road.py --nogui --seconds 120 # 화면 없이 설정 오류·차량 투입 확인
python collect_pomdp_data.py --policy keep-lane --episodes 1 --gui --name env_check   # 환경 1 에피소드 점검
python train.py                           # PPO 학습
python test.py results/run_폴더/model.pt --episodes 100 --nogui   # 최종 평가
```

## 6. 역할 분담 예시

| 역할 | 주요 작업 | 관련 파일 |
|---|---|---|
| 도로 구축 | 실제 도로 조사, Node·Edge·Connection·Route 구현 | `road_config.py`, `road_builder.py` |
| 교통 환경 | 일반 차량 종류·속도·교통량·경로 | `road_config.py`, `road_builder.py` |
| AV 환경 | Observation·Action·Reward·종료 조건 | `mdp_config.py`, `sumo_env.py` |
| 모델 학습 | PPO/BC 학습, 하이퍼파라미터 실험 | `train.py`, `train_bc.py`, `algorithms/` |
| 평가·데이터 | 반복 평가, 그래프, 데이터셋, 영상 | `test.py`, `collect_pomdp_data.py`, `utils/` |

파일만 나눠 맡지 말고, 아래 연결 지점은 **팀 전체가 함께 확인**한다.

```text
도로 Route ↔ ego 생성 위치      도로 차선 ↔ Observation
Action ↔ 실제 SUMO 제어          종료 조건 ↔ 목적지
Reward ↔ 평가 지표               학습 환경 ↔ 평가·데이터 수집 환경
```
