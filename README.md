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
- **복잡한 도로보다, 프로젝트의 목적과 차량 interaction이 명확하게 드러나는 환경**을 높게 평가한다.
- 최종 통과 기준: **Collision Rate < 5%**, **목적지 완주**, **충분한 일반 차량** — 자세한 내용은 [평가 기준](docs/evaluation.md)

## 📅 일정

| 일정 | 날짜 | 형식 |
|---|---|---|
| **정기 회의** | **매주 화요일** (수업 날) | 회의별 목표는 [진행 계획 — 회의 일정](docs/roadmap.md#회의-일정) |
| **중간발표** | **11/10(화) 예상** (확정 시 수정) | 3분 — 도로 선정 이유, 구조 특징, interaction, 데이터 컬럼, 역할 분담 |
| **최종발표** | **11/28(토) 13:00~19:00** | 13분 — 전체 과정 + **30초 이상 주행 영상** + 동료 평가 |
| 최종 제출 | 확정 시 기입 | 프로젝트 페이지, 코드, 발표자료, Hugging Face 데이터 |

할 일 순서는 [진행 계획](docs/roadmap.md)에 있다.

## 👥 팀원

| 이름 | GitHub ID | 담당 |
|---|---|---|
| 박준수 | a01023289522-cmd | 미정 |
| 최민기 | mingi-eee | 미정 |
| 임재성 | imjaeseong970-cpu | 미정 |
| 임수진 | sUUjin-L | 미정 |

역할 분담 예시는 [프로젝트 개요 — 역할 분담](docs/project_overview.md#6-역할-분담-예시)을 참고해서 정한다.

## 🚀 처음 들어온 팀원이 할 일

1. GitHub에서 이 저장소 **초대(invitation) 수락** (수락해야 push·PR 등 쓰기 권한이 생긴다)
2. **[Git 협업 가이드](docs/git_guide.md)** 읽고 Git 프로그램 준비(**GitHub Desktop 권장**, 익숙한 것 아무거나 OK) → 이 저장소 Clone
3. **[평가 기준과 발표 일정](docs/evaluation.md)** 읽기 — **가장 중요한 문서.** 모든 결정은 여기 기준으로 검토한다
4. **[프로젝트 개요](docs/project_overview.md)** 읽기 — 무엇을 만드는지, 수업 코드 구조
5. **[한국 도로의 특징](docs/korean_road_features.md)** 읽기 — 도로에 넣을 "한국다운" 요소
6. **[진행 계획](docs/roadmap.md)** 에서 현재 단계와 내 할 일 확인

## 📚 문서

| 문서 | 내용 |
|---|---|
| [docs/evaluation.md](docs/evaluation.md) | ⭐ **평가 기준과 발표 일정** — 중간·최종발표 내용, 통과 기준, 동료 평가, 제출물, 결정 점검표 |
| [docs/project_overview.md](docs/project_overview.md) | 프로젝트 주제, 평가 기준, 진행 단계, 수업 코드 구조 요약 |
| [docs/roadmap.md](docs/roadmap.md) | 일정, **할 일 순서**, 실험·문제 해결·결정·회의 기록 — **진행하면서 채워 나가는 곳** |
| [docs/korean_road_features.md](docs/korean_road_features.md) | 한국 도로의 특징(교통 규칙·속도·구조)과 SUMO 구현 방법 |
| [docs/sumo_reference.md](docs/sumo_reference.md) | SUMO 공식 문서 찾는 법, 자주 쓰는 페이지, 신호등 기본 사용법 |
| [docs/git_guide.md](docs/git_guide.md) | Git 프로그램 고르기(GitHub Desktop 권장), GitHub Desktop·Fork 사용법, pull·push·merge 개념, 팀 규칙 |

## 🔗 수업 원본 저장소

- https://github.com/bmil-ssu/Artificial-Intelligence-and-Control-for-Autonomous-Driving
- 수업 코드와 강의 문서는 계속 업데이트되므로 **이 저장소에 복사해 두지 않는다.** 필요할 때 원본을 직접 본다.
- 실제 코드 작업을 시작할 때 어떻게 가져올지는 [진행 계획 — 코드 작업 시작](docs/roadmap.md#코드-작업-시작-방법-정해지면-채우기)에서 정한다.

## 🤝 협업 규칙 (요약)

- `main` 브랜치는 **항상 실행되는 상태**로 유지한다. 직접 수정하지 않는다. (GitHub 설정으로 보호됨: PR + 팀원 1명 승인 필요)
- 작업은 **브랜치**에서 하고, **Pull Request(PR)** 로 `main`에 합친다. 다른 팀원 1명이 확인 후 합친다.
- 작업 시작 전에 항상 **Pull** 로 최신 상태를 받는다.
- 학습 결과(`results/`), 큰 데이터 파일은 올리지 않는다. 데이터셋은 HuggingFace에 올린다.

자세한 방법은 [Git 협업 가이드](docs/git_guide.md)에 있다.
