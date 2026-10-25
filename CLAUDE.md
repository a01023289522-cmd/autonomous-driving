# 프로젝트 규칙 (Claude Code용)

이 저장소는 "자율주행 인공지능 및 제어" 수업의 팀 프로젝트 저장소다.
**평가 기준은 `docs/evaluation.md`**, 진행 상황은 `docs/roadmap.md`, 프로젝트 개요는 `docs/project_overview.md`를 먼저 읽는다.

## 규칙 0. 모든 결정은 평가 기준으로 검토한다 (가장 중요)

도로 선정, 도로·교통 구현, AV 관측·행동·보상, 데이터 컬럼, 학습·평가, 발표·제출물에 관한 제안이나 작업은
진행 전에 `docs/evaluation.md`의 **"결정할 때마다 쓰는 점검표"** 로 검토하고, 어떤 항목과 연결되는지 함께 밝힌다.

- 핵심: **복잡한 도로보다 목적과 차량 interaction이 명확한 환경**을 높게 평가한다.
- 흐름: 왜 이 도로 → 어떤 interaction → AV가 안정적으로 해결 → 데이터에 기록
- 통과 기준: Collision Rate < 5%, 목적지 완주(Start → Goal), 충분한 일반 차량, 시뮬레이션 안정성, State(절대 정보) 데이터 컬럼
- 점검표 항목과 어긋나는 방향이면 진행 전에 그 점을 사용자에게 알린다.
- 겪은 문제와 해결은 `docs/roadmap.md`의 "문제와 해결 기록"에 남긴다 (최종발표·동료평가 항목).

## 규칙 1. SUMO 관련 작업은 항상 SUMO 공식 문서부터 확인한다

SUMO와 관련된 작업이면 **무엇을 하든 시작 전에 한 번** SUMO 문서를 확인하고, 그 내용을 근거로 진행한다.
추측이나 기억으로 SUMO 속성·옵션·API를 쓰지 않는다.

- 적용 대상: 도로 구조(노드·엣지·차선·연결·교차로·신호등), 차량·교통(vType·route·flow·차량 모델),
  SUMO XML 생성·수정, `netconvert`·`netedit`·`sumo`·`sumo-gui` 옵션, TraCI·`sumolib` 사용,
  SUMO 동작 설명과 경고·오류 분석
- 확인 순서와 자주 쓰는 페이지 목록: `docs/sumo_reference.md`
  1. 로컬 설치 문서 `SUMO_HOME/doc/userdoc/` (Windows: `C:\Program Files (x86)\Eclipse\Sumo\doc\userdoc\`)
  2. XML 규격 `SUMO_HOME/data/xsd/`
  3. 공식 도구 `SUMO_HOME/tools/` — 직접 만들기 전에 이미 있는지 확인
  4. 로컬에 없을 때만 웹 문서 https://sumo.dlr.de/docs/ (버전 차이 주의)
- 설명·보고할 때 참고한 문서 페이지를 함께 밝힌다.
- 문서 내용과 코드가 다르면 그 차이를 알린다.
- SUMO 관련 변경 후에는 실제로 실행해서 검증한다.

## 규칙 2. 협업 규칙을 따른다

- `main`에 직접 커밋하지 않는다. `이름/작업내용` 브랜치에서 작업하고 PR로 합친다.
- 커밋 메시지는 `분류: 내용` (예: `도로: 사거리 노드 추가`).
- 실험·결정은 `docs/roadmap.md`에 기록한다.
