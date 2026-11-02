# SUMO 도로망 (성균관대역 일대)

박준수 작업물. 도로망·교통·보기 도구가 모두 `skku_map/`에 있다.

| 폴더 | 내용 |
|---|---|
| [`skku_map/`](skku_map/) | **현재 도로망.** 사용법·파일 설명은 [`skku_map/README.md`](skku_map/README.md) |
| [`skku_map/HISTORY.md`](skku_map/HISTORY.md) | ⭐ **만든 과정과 시행착오** (1차 → 2차 → 3차, 무엇이 왜 안 됐는지) |
| [`skku_map/WORKLOG.md`](skku_map/WORKLOG.md) | 날짜별 작업 기록, 위성사진 차로 조사 결과 |
| `course_repo_changes/` | 수업 저장소(bmil-ssu) 코드에 한 수정분: `course_repo.patch`(`env/`, `view_road.py`), 학습률 실험 스크립트. `BASE_COMMIT.txt`의 커밋 위에 `git apply`로 적용 |

앞선 시도(`skku_area`, `skku_schematic`, `underpass`)는 정리하면서 뺐다 (git 기록 커밋 03c35e9에 남아 있다).

## 바로 보기
SUMO 1.27.1 설치 후 (Windows):
```
cd sumo/skku_map
run_skku.bat
```
또는 `python -X utf8 view_skku.py`. 도로망을 다시 만들려면 `python -X utf8 build.py` (OSM 원본은 `skku_map/osm/`).
