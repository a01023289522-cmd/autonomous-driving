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
| 박준수 | | 미정 |
| 최민기 | | 미정 |
| 임재성 | | 미정 |
| 임수진 | | 미정 |

역할 분담 예시는 [프로젝트 개요 — 역할 분담](docs/project_overview.md#6-역할-분담-예시)을 참고해서 정한다.

## 🚀 처음 들어온 팀원이 할 일

1. GitHub에서 이 저장소 **초대(invitation) 수락** (비공개 저장소라 초대받아야 보인다)
2. **[Git 협업 가이드](docs/git_guide.md)** 읽고 Git 프로그램 준비(**GitHub Desktop 권장**, 익숙한 것 아무거나 OK) → 이 저장소 Clone
3. **[프로젝트 개요](docs/project_overview.md)** 읽기 — 무엇을 만들고 어떻게 평가받는지
4. **[한국 도로의 특징](docs/korean_road_features.md)** 읽기 — 평가 1순위가 "한국 도로 특징 반영"
5. **[진행 계획](docs/roadmap.md)** 에서 현재 단계와 내 할 일 확인

## 📚 문서

| 문서 | 내용 |
|---|---|
| [docs/project_overview.md](docs/project_overview.md) | 프로젝트 주제, 평가 기준, 진행 단계, 수업 코드 구조 요약 |
| [docs/roadmap.md](docs/roadmap.md) | 단계별 체크리스트, 결정 기록, 회의 기록 — **진행하면서 채워 나가는 곳** |
| [docs/korean_road_features.md](docs/korean_road_features.md) | 한국 도로의 특징(교통 규칙·속도·구조)과 SUMO 구현 방법 |
| [docs/sumo_reference.md](docs/sumo_reference.md) | SUMO 공식 문서 찾는 법, 자주 쓰는 페이지, 신호등 기본 사용법 |
| [docs/git_guide.md](docs/git_guide.md) | Git 프로그램 고르기(GitHub Desktop 권장), GitHub Desktop·Fork 사용법, pull·push·merge 개념, 팀 규칙 |

## 🔗 수업 원본 저장소

- https://github.com/bmil-ssu/Artificial-Intelligence-and-Control-for-Autonomous-Driving
- 수업 코드와 강의 문서는 계속 업데이트되므로 **이 저장소에 복사해 두지 않는다.** 필요할 때 원본을 직접 본다.
- 실제 코드 작업을 시작할 때 어떻게 가져올지는 [진행 계획 — 코드 작업 시작](docs/roadmap.md#코드-작업-시작-방법-정해지면-채우기)에서 정한다.

## 🤝 협업 규칙 (요약)

- `main` 브랜치는 **항상 실행되는 상태**로 유지한다. 직접 수정하지 않는다.
- 작업은 **브랜치**에서 하고, **Pull Request(PR)** 로 `main`에 합친다. 다른 팀원 1명이 확인 후 합친다.
- 작업 시작 전에 항상 **Pull** 로 최신 상태를 받는다.
- 학습 결과(`results/`), 큰 데이터 파일은 올리지 않는다. 데이터셋은 HuggingFace에 올린다.

자세한 방법은 [Git 협업 가이드](docs/git_guide.md)에 있다.
