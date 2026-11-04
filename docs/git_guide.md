# Git 협업 가이드

1. 어떤 프로그램으로 Git을 쓸지 (**GitHub Desktop 권장**)
2. GitHub Desktop 시작하기
3. (선택) Fork 사용법
4. Git 기본 개념 — pull, push, merge
5. 팀 규칙

---

## 1. Git 프로그램 고르기

이 저장소는 GitHub에 있으므로, **어떤 Git 프로그램을 써도 똑같이 협업할 수 있다.**
팀원마다 다른 프로그램을 써도 문제없다. 처음이면 **GitHub Desktop**으로 시작한다.

| 프로그램 | 가격 | 특징 |
|---|---|---|
| **GitHub Desktop** (권장) | 무료 | GitHub 공식 프로그램. 가장 단순하고, **공식 한국어 안내 문서**가 있어 혼자 익히기 쉬움 |
| Fork | 무료 평가판 (정식 라이선스 유료) | 빠르고 화면이 깔끔함. 브랜치 그래프·충돌 해결 화면이 보기 좋음 |
| VS Code 내장 Git | 무료 | 코드 편집하면서 바로 커밋·푸시. 추가 설치 없음 |
| 명령어 (`git`) | 무료 | 모든 기능 사용 가능. 익숙해지면 가장 빠름 |

---

## 2. GitHub Desktop 시작하기

공식 안내 문서(한국어): https://docs.github.com/ko/desktop

### 2-1. 처음 한 번만
1. **설치**: https://desktop.github.com (Windows / Mac — 주소를 열면 GitHub Desktop 다운로드 페이지로 이동)
2. **GitHub 로그인**: 처음 실행 시 `Sign in to GitHub.com` → 브라우저에서 로그인·승인
3. **저장소 초대 수락**: GitHub 이메일 또는 https://github.com/notifications 에서 초대를 수락한다 (수락해야 push·PR 권한이 생김).
4. **Clone (내 컴퓨터로 받기)**: `File → Clone repository…` → `GitHub.com` 탭에서 `a01023289522-cmd/autonomous-driving` 선택 → 저장할 폴더 지정 → `Clone`

### 2-2. 화면에서 찾을 것
| 위치 | 하는 일 |
|---|---|
| 위쪽 **Current repository** | 작업할 저장소 고르기 |
| 위쪽 **Current branch** | 브랜치 이동, `New branch`로 새 브랜치 만들기 |
| 위쪽 오른쪽 **Fetch origin / Pull origin / Push origin** | 상황에 따라 글자가 바뀌는 버튼. 새 변경이 있으면 Pull, 내 커밋이 있으면 Push |
| 왼쪽 **Changes** 탭 | 내가 바꾼 파일과 줄 (초록 = 추가, 빨강 = 삭제) |
| 왼쪽 **History** 탭 | 전체 변경 기록 |
| 왼쪽 아래 **Summary + Commit to …** | 커밋 메시지 쓰고 커밋 |

### 2-3. 매번 하는 작업 흐름
1. Current branch를 **main**으로 → **Fetch origin → Pull origin** (최신 받기)
2. **Current branch → New branch** → 이름 `이름/작업내용` (예: `minki/reward-signal`)
3. 파일 수정 → **Changes** 탭에서 바뀐 줄 확인
4. 왼쪽 아래 Summary에 `분류: 내용` (예: `보상: 신호 위반 감점 추가`) → **Commit to 브랜치이름**
5. **Publish branch** (처음) / **Push origin** (그 다음부터)
6. **Create Pull Request** 버튼 → GitHub 웹페이지에서 설명 작성 → 팀원 1명 Reviewer 지정 → 확인 후 **Merge**
7. GitHub Desktop에서 main으로 돌아와 **Pull origin** → 다음 작업은 다시 1번부터

---

## 3. (선택) Fork 사용법

> 메뉴 이름·위치는 Fork 버전이나 Windows/Mac에 따라 조금 다를 수 있다.

### 3-1. 처음 한 번만
1. **설치**: https://git-fork.com (Windows / Mac)
2. **이름·이메일**: 설정에서 Git 이름·이메일을 GitHub 계정 이메일로 맞춘다 (커밋에 작성자로 남음).
3. **GitHub 계정 연결**: Windows `File → Accounts` / Mac `Fork → Settings → Accounts` → `+` → GitHub → 브라우저에서 로그인.
4. **저장소 초대 수락**: GitHub 이메일 또는 https://github.com/notifications 에서 초대를 수락한다 (수락해야 push·PR 권한이 생김).
5. **Clone (내 컴퓨터로 받기)**: `File → Clone…` → URL `https://github.com/a01023289522-cmd/autonomous-driving.git` → 폴더 선택.

### 3-2. 화면 구성
```text
┌───────────────┬──────────────────────────────────────────────┐
│ 왼쪽 사이드바   │  가운데: 커밋 기록 그래프 / 바뀐 파일과 줄            │
│ Local Changes │  ← 내가 바꾼 파일 (아직 커밋 안 한 것)              │
│ All Commits   │  ← 전체 변경 기록                                │
│ Branches      │  ← 내 컴퓨터의 브랜치 (더블클릭 = 이동)             │
│ Remotes       │  ← GitHub에 있는 브랜치                          │
├───────────────┴──────────────────────────────────────────────┤
│ 위쪽 툴바: Fetch · Pull · Push · Stash · Branch …              │
└──────────────────────────────────────────────────────────────┘
```

| 기능 | 하는 일 |
|---|---|
| **Fetch** | GitHub에 새 변경이 있는지 **확인만** (내 파일은 그대로) |
| **Pull** | GitHub의 최신 변경을 **받아서 내 파일에 반영** |
| **Push** | 내 커밋을 **GitHub에 올림** |
| **Branch** | 새 작업 브랜치 만들기 |
| **Stash** | 커밋 안 한 변경을 잠깐 치워두기 |
| **File History / Blame** | 파일 오른쪽 클릭 → 그 파일의 변경 이력 / 줄마다 마지막으로 바꾼 사람 |

### 3-3. 매번 하는 작업 흐름
1. `Branches`에서 **main 더블클릭 → Pull** (최신 받기)
2. **Branch** → 이름 `이름/작업내용` (예: `junsoo/road-intersection`) → 만들고 이동
3. 파일 수정 → **Local Changes**에서 바뀐 줄 확인 (초록 = 추가, 빨강 = 삭제)
4. 올릴 파일 **Stage** → 커밋 메시지 `분류: 내용` (예: `도로: 사거리 노드 추가`) → **Commit**
5. **Push** (처음 올리는 브랜치면 GitHub에 같은 이름으로 생김)
6. GitHub 저장소 페이지의 **`Compare & pull request`** → 설명 작성 → 팀원 1명 Reviewer 지정 → 확인 후 **Merge**
7. Fork에서 main으로 돌아와 **Pull** → 다음 작업은 다시 1번부터

### 3-4. 충돌이 났을 때
- 충돌 난 파일이 Local Changes에 경고 아이콘으로 표시된다.
- 파일을 누르면 **내 것(Ours)** 과 **상대 것(Theirs)** 을 비교하는 화면 → 남길 쪽을 고르거나 직접 합침 → 저장 → Stage → Commit.
- 판단이 어려우면 바로 커밋하지 말고 그 부분을 고친 팀원과 상의한다.

---

## 4. Git 기본 개념

### 저장소는 두 군데에 있다
```text
   GitHub (원격 저장소, remote)          ← 팀 전체가 공유하는 원본
        ▲  push            │  pull
        │                  ▼
   내 컴퓨터 (로컬 저장소, local)         ← 각자 작업하는 복사본
```

| 용어 | 뜻 |
|---|---|
| **clone** | GitHub 저장소를 내 컴퓨터로 **처음 한 번** 통째로 받기 |
| **commit** | 지금까지 바꾼 내용을 **하나의 기록(저장 지점)** 으로 남기기. 아직 내 컴퓨터에만 있음 |
| **push** | 내 커밋들을 **GitHub에 올리기**. 이때부터 팀원이 볼 수 있음 |
| **pull** | GitHub에 올라온 남의 커밋을 **내 컴퓨터로 받아 합치기** (= fetch + merge) |
| **fetch** | GitHub에 새 커밋이 있는지 **받아만 오고 합치지는 않기** |
| **branch** | `main`에서 갈라져 나온 **나만의 작업 줄기**. 여기서 실험해도 main은 안전함 |
| **merge** | 두 브랜치의 변경을 **하나로 합치기** (예: 내 작업 브랜치 → main) |
| **Pull Request (PR)** | GitHub에서 "내 브랜치를 main에 merge해도 될까요?" 하고 **확인을 요청**하는 것 |
| **conflict (충돌)** | 두 사람이 **같은 파일의 같은 부분**을 다르게 고쳐서 Git이 자동으로 합치지 못하는 상황 |

### 브랜치와 merge 그림
```text
main     ──●────────●──────────────●────   (항상 실행되는 상태)
            \                     /
my-branch    ●──●──●  (내 작업) ──┘  ← PR로 확인 후 merge
```

### 왜 push 전에 pull을 하나
내가 작업하는 동안 다른 팀원이 GitHub에 먼저 올렸으면, 내 컴퓨터의 기록이 뒤처진 상태다.
그 상태로 push하면 거절(rejected)된다. **pull로 남의 변경을 먼저 받아 합친 뒤 push**한다.

---

## 5. 팀 규칙

| 규칙 | 이유 |
|---|---|
| `main`에 직접 커밋하지 않는다 | main은 항상 실행되는 상태로 유지 (GitHub 설정으로 보호됨 — PR + 팀원 1명 승인이 있어야 merge 가능) |
| 작업 전 항상 pull | 충돌 예방 |
| 브랜치 이름 `이름/작업내용` | 누가 무슨 작업 중인지 바로 보임 |
| 커밋 메시지 `분류: 내용` | 기록만 봐도 무엇이 바뀌었는지 알 수 있음 |
| PR은 팀원 1명 확인 후 merge | 실수 방지, 서로 작업 공유 |
| 작은 단위로 자주 커밋·PR | 충돌이 작아지고 되돌리기 쉬움 |
| `results/`, 큰 데이터, `__pycache__` 는 올리지 않는다 | 저장소가 무거워짐 (`.gitignore`에 등록됨) |
| 실험·결정은 [진행 계획](roadmap.md)에 기록 | 보고서 쓸 때 근거가 됨 |

### 자주 하는 실수
| 상황 | 해결 |
|---|---|
| push가 거절됨 (rejected) | 그 사이 다른 사람이 올린 것. **pull 먼저** 하고 다시 push |
| main에서 작업해버림 | 커밋 전이면 새 브랜치를 만들면 변경도 같이 따라온다 |
| 커밋 메시지를 잘못 씀 | push 전이면 마지막 커밋 메시지 수정(Amend) 가능 |
| 바꾼 내용 되돌리기 (Discard) | **커밋 안 한 변경은 되돌리면 영영 사라진다.** 신중하게 |
| push가 권한 오류로 안 됨 | GitHub 초대를 수락했는지 확인 |
