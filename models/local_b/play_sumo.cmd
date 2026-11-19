@echo off
setlocal
if not defined COURSE_REPO if exist "%USERPROFILE%\Artificial-Intelligence-and-Control-for-Autonomous-Driving\env\sumo_env.py" set "COURSE_REPO=%USERPROFILE%\Artificial-Intelligence-and-Control-for-Autonomous-Driving"
python -X utf8 "%~dp0replay.py" %*
if errorlevel 1 (
    pause
    exit /b 1
)
