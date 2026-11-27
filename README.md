# 자율주행 팀 프로젝트

> **자율주행 인공지능 및 제어** 수업 팀 프로젝트
> SUMO 시뮬레이터로 **대한민국 실제 도로**를 구현하고, 그 위에서 자율주행 차량(AV)을 학습시킨다.

## 🎯 목표

> **"우리가 만든 한국 도로 위에서, 우리가 학습시킨 자율주행 차량이 스스로 주행하도록 만들기"**

```text
실제 도로 선정 → SUMO 도로 구현 → 일반 차량 교통 → AV 관측·행동·보상 정의
→ 모델 학습 (PPO / BC) → 주행 데이터 수집 → 평가·결과물 정리
```

- 핵심은 **새 알고리즘이 아니라, 도로 환경과 시뮬레이션의 완성도**다.
- 기본 목표: **충돌률(Collision Rate) ≤ 5%** (100 에피소드 이상 평가 기준)

## 👥 팀원

| 이름 | GitHub ID | 담당 |
|---|---|---|
| 박준수 | a01023289522-cmd | SUMO 도로망 구축 · 학습 환경 연결 · 주행 데이터 수집과 Hugging Face 공개 |
| 최민기 | mingi-eee | 모델 추가 학습과 정차 평가 · 데이터 수집기 · 프로젝트 웹페이지 |
| 임재성 | imjaeseong970-cpu | 보상·관측 설계 · NW7 학습 · 최종 모델 선정과 평가 · 주행 영상 |
| 임수진 | sUUjin-L | 정문 신호·정지선 반복 평가 · 적색 진입과 정지 위치 평가 도구 |

## 🏁 최종 모델 NW7

- 모델: [`models/jaeseong_1125_nw7.pt`](models/jaeseong_1125_nw7.pt), 설정 `js_nw7`, 설명·학습 명령: [`models/jaeseong_1125_nw7.md`](models/jaeseong_1125_nw7.md)
- 결과 (학습에 쓰지 않은 교통 시드 2000–2999, 1,000회): 완주 97.5%, 충돌 2.5%, 적색 신호 진입 0회
- 프로젝트 페이지: https://a01023289522-cmd.github.io/autonomous-driving/docs/ · 주행 데이터: https://huggingface.co/datasets/jnsoo/autonomous_driving

```
python -X utf8 rl/test_skku.py models/jaeseong_1125_nw7.pt --config js_nw7 --episodes 1                     # SUMO 화면 주행
python -X utf8 rl/quick_eval.py models/jaeseong_1125_nw7.pt --config js_nw7 --seeds 2000-2999 --procs 4    # 화면 없이 평가
python -X utf8 rl/collect_nw7.py --workers 2                                                                 # 주행 데이터 수집 (Windows)
```

## 🚀 시작하기

1. 이 저장소와 [수업 저장소](https://github.com/bmil-ssu/Artificial-Intelligence-and-Control-for-Autonomous-Driving)를 **같은 상위 폴더**에 clone한다 (`rl/course.py`가 옆 폴더의 수업 코드를 찾는다)
2. 설치·확인 명령: [작업 가이드 3장 초기 설정](docs/work_guide.md)
3. 학습·평가·수집 명령: [작업 가이드 4장](docs/work_guide.md), 개념: [개념 정리](docs/concepts.md)
4. 지금까지의 결과와 환경 버전: [실험 기록표](docs/experiments.md)

## 📁 구성

| 폴더 | 내용 |
|---|---|
| `rl/` | 성대역 환경(`skku_env.py`), 실험 설정(`configs/`), 학습·평가·수집 스크립트, 데이터 칼럼 정의(`columns.py`) |
| `sumo/skku_map/` | 성대역 일대 SUMO 도로망·교통·보기 도구. 사용법은 [`sumo/skku_map/README.md`](sumo/skku_map/README.md) |
| `docs/` | 문서 (아래 표) |

학습 결과(`results/`), 수집 데이터(`data/`), 배경 교통 상태 파일(`sumo/skku_map/work/`)은 올리지 않는다.

## 📚 문서

| 문서 | 내용 |
|---|---|
| [docs/evaluation.md](docs/evaluation.md) | **평가 기준, 일정, 통과 기준, 데이터 규칙, 11/17 컨설팅 공지, 결정할 때 쓰는 점검표** |
| [docs/concepts.md](docs/concepts.md) | 개념 정리: 기준선·BC·PPO, 보상과 학습의 관계, 실행 명령 |
| [docs/work_guide.md](docs/work_guide.md) | 작업 가이드: 확정 사항, 팀원별 작업, 사용법 |
| [docs/experiments.md](docs/experiments.md) | 실험 기록표 |
| [docs/project_overview.md](docs/project_overview.md) | 프로젝트 주제, 평가 기준, 진행 단계, 수업 코드 구조 요약 |
| [docs/korean_road_features.md](docs/korean_road_features.md) | 한국 도로의 특징(교통 규칙·속도·구조)과 SUMO 구현 방법 |
| [docs/sumo_reference.md](docs/sumo_reference.md) | SUMO 공식 문서 찾는 법, 자주 쓰는 페이지, 신호등 기본 사용법 |
| [docs/git_guide.md](docs/git_guide.md) | Git 프로그램 고르기(GitHub Desktop 권장), GitHub Desktop·Fork 사용법, pull·push·merge 개념, 팀 규칙 |

## 🔗 수업 원본 저장소

- https://github.com/bmil-ssu/Artificial-Intelligence-and-Control-for-Autonomous-Driving
- 수업 코드와 강의 문서는 계속 업데이트되므로 **이 저장소에 복사해 두지 않는다.** 필요할 때 원본을 직접 본다.
- 수업 코드는 `rl/course.py`가 옆 폴더(또는 환경 변수 `COURSE_REPO`)에서 불러 쓴다. 수업 코드는 고치지 않는다.

## 🤝 협업 규칙 (요약)

- `main` 브랜치는 **항상 실행되는 상태**로 유지한다. 직접 수정하지 않는다.
- 작업은 **브랜치**에서 하고, **Pull Request(PR)** 로 `main`에 합친다. 다른 팀원 1명이 확인 후 합친다.
- 작업 시작 전에 항상 **Pull** 로 최신 상태를 받는다.
- 학습 결과(`results/`), 큰 데이터 파일은 올리지 않는다. 데이터셋은 HuggingFace에 올린다.

자세한 방법은 [Git 협업 가이드](docs/git_guide.md)에 있다.
