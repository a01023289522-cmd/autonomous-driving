"""수업 저장소 코드를 import할 수 있게 경로를 잡는다. 수업 코드는 이 저장소에 복사하지 않는다 (README 참고).

찾는 순서: 환경변수 COURSE_REPO → 이 저장소와 나란히 있는 수업 저장소 폴더.
rl/ 의 스크립트는 다른 import보다 먼저 `import course` 한다.
"""
import os
import sys

TEAM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_NAME = "Artificial-Intelligence-and-Control-for-Autonomous-Driving"


def _find():
    for path in (os.environ.get("COURSE_REPO"), os.path.join(os.path.dirname(TEAM), _NAME)):
        if path and os.path.isfile(os.path.join(path, "env", "sumo_env.py")):
            return path
    raise SystemExit(f"수업 저장소를 못 찾았습니다. 이 저장소 옆에 {_NAME} 폴더로 clone하거나 환경변수 COURSE_REPO에 경로를 지정하세요.")


COURSE = _find()
if COURSE not in sys.path:
    sys.path.insert(0, COURSE)
