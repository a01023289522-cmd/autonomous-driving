# SUMO 참고 자료

SUMO 관련 작업(도로, 차량, 신호등, netconvert 옵션, TraCI 등)은 **추측하지 말고 공식 문서를 먼저 확인한다.**

---

## 문서 찾는 순서

1. **내 컴퓨터에 설치된 공식 문서** (설치한 SUMO 버전과 정확히 일치 — 1순위)
   - Windows: `C:\Program Files (x86)\Eclipse\Sumo\doc\userdoc\index.html`
   - 그 외: `SUMO_HOME` 환경변수 폴더 아래 `doc/userdoc/` (설치 방식에 따라 없을 수 있음 → 3번으로)
   - 브라우저로 `index.html`을 열면 웹 문서와 같은 화면으로 볼 수 있다.
2. **XML 속성 규격**: `SUMO_HOME/data/xsd/` (`nodes_file.xsd`, `edges_file.xsd`, `routes_file.xsd`, `additional_file.xsd` 등)
3. **웹 문서**: https://sumo.dlr.de/docs/
   최신 버전 기준이라 설치 버전(수업 기준 1.27.1)과 다를 수 있다.
4. **이미 있는 도구인지 확인**: `SUMO_HOME/tools/` (예: `randomTrips.py`, `osmWebWizard.py`) — 직접 만들기 전에 확인.

## 자주 쓰는 페이지 (`doc/userdoc/` 기준, 웹은 `https://sumo.dlr.de/docs/` 뒤에 같은 경로)

| 주제 | 페이지 |
|---|---|
| 노드·엣지·연결 정의 (plain XML) | `Networks/PlainXML.html` |
| netconvert 옵션 | `netconvert.html` |
| netedit 사용법 | `Netedit/index.html` |
| 차량·vType·route·flow 정의 | `Definition_of_Vehicles,_Vehicle_Types,_and_Routes.html` |
| vType 기본값 | `Vehicle_Type_Parameter_Defaults.html` |
| 차량 추종 모델 (Krauss, IDM 등) | `Car-Following-Models.html` |
| 신호등 | `Simulation/Traffic_Lights.html` |
| 교차로 | `Simulation/Intersections.html` |
| 차량 투입 | `Simulation/VehicleInsertion.html` |
| 순간이동(teleport) 원인 | `Simulation/Why_Vehicles_are_teleporting.html` |
| 안전 거리·충돌 | `Simulation/Safety.html` |
| TraCI 개요 | `TraCI.html` |
| TraCI 차량 제어 (speedMode, changeLane 등) | `TraCI/Change_Vehicle_State.html` |
| TraCI 차량 정보 조회 | `TraCI/Vehicle_Value_Retrieval.html` |
| TraCI 신호등 제어·조회 | `TraCI/Change_Traffic_Lights_State.html`, `TraCI/Traffic_Lights_Value_Retrieval.html` |
| sumo / sumo-gui 옵션 | `sumo.html`, `sumo-gui.html` |
| 실제 지도(OSM) 가져오기 | `Tools/Import/OSM.html`, `Tutorials/OSMWebWizard.html` |
| 무작위 경로 생성 | `Tools/Trip.html` |
| XML 검증 | `XMLValidation.html` |

### 문서 안에서 단어 검색 (Git Bash / Mac 터미널)
HTML 태그를 지우고 검색하면 편하다.
```bash
sed -e 's/<[^>]*>//g' "$SUMO_HOME/doc/userdoc/Simulation/Traffic_Lights.html" | grep -i -n "cycle"
```

---

## 신호등 기본 사용법

출처: `Simulation/Traffic_Lights.html`, `Networks/PlainXML.html`, `netconvert.html`, `TraCI/Change_Vehicle_State.html`

### 1. 노드를 신호 교차로로 지정하면 SUMO가 신호 프로그램을 자동으로 만든다
```xml
<node id="J1" x="0" y="0" type="traffic_light"/>
```
- `netconvert`가 교차로 모양에 맞는 신호 프로그램을 자동 생성한다. **기본값으로 충분하면 따로 만들 필요 없다.**
- 기본 주기 90초 (`--tls.cycle.time`), 황색 시간은 진입 도로 제한속도로 자동 계산.
- 마주치는 흐름이 없는 신호(직선 도로 위 신호 등)의 적색 시간은 `--tls.red.time`(기본 5초).

### 2. 신호 종류 (`tlType`)
노드에 `tlType`을 주거나, `netconvert --tls.default-type` 으로 전체 기본값을 바꾼다. 생략하면 `static`.

| tlType | 동작 |
|---|---|
| `static` | 고정 주기 (기본) |
| `actuated` | 자동 생성된 검지기로 차량 간격을 보고 녹색 시간을 늘리거나 줄임 |
| `delay_based` | 차량 대기 시간 기준으로 조절 |
| `NEMA` | 미국식 교차로 신호 표준 |

### 3. 시간만 바꾸고 싶을 때 — netconvert 옵션
| 옵션 | 의미 |
|---|---|
| `--tls.cycle.time` | 전체 주기 (기본 90) |
| `--tls.green.time` | 녹색 시간 (기본 31) |
| `--tls.yellow.time` | 황색 시간 고정 |
| `--tls.red.time` | 마주치는 흐름 없는 신호의 적색 시간 (기본 5) |
| `--tls.allred.time` | 신호 바뀔 때 전방향 적색 시간 (기본 0) |

### 4. 단계를 직접 정해야 할 때 (고급)
`additional` 파일에 `<tlLogic>`을 정의하면 자동 생성된 프로그램 대신 쓸 수 있다. 기본값과 옵션으로 안 될 때만 쓴다.

### 5. GUI에서 확인
sumo-gui에서 신호등을 **오른쪽 클릭 → `Show Phases` / `Track Phases`** 로 현재 단계와 주기를 볼 수 있다.

### ⚠️ 자율주행 차량(ego)은 기본적으로 신호를 지키지 않는다
- 수업 코드 `env/sumo_env.py`는 강화학습 제어를 위해 ego의 안전장치를 모두 끈다 (`traci.vehicle.setSpeedMode(ego, 0)`).
- TraCI 문서상 speedMode **bit4 = "적색 신호를 지나지 않도록 급제동"** 도 같이 꺼진다 → 앞이 비어 있으면 적색에도 통과할 수 있다.
- 또 현재 관측(31차원)에는 **신호 상태가 없다.**
- 신호를 지키게 하려면: 관측에 신호 상태·정지선까지 거리 추가 (`_get_obs()`, `observation_space`) + 보상에 신호 위반 감점 추가 (`step()`) 후 재학습.

---

## 그 외 메모 (진행하면서 추가)

-
