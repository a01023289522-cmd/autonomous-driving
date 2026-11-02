@echo off
rem SKKU station SUMO viewer (double-click, or use the desktop shortcut)
rem   run_skku.bat [1|2|3]   1 = simulation with cars and buses   2 = roads only   3 = rebuild network (build.py) then simulate
cd /d "%~dp0"
if "%SUMO_HOME%"=="" set "SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo"
set "GUI=%SUMO_HOME%\bin\sumo-gui.exe"

if exist skku.net.xml goto :menu
echo Network file not found. Building it first (1-2 min)...
python -X utf8 build.py --no-check || goto :fail

:menu
set "MODE=%~1"
if not "%MODE%"=="" goto :run
echo.
echo  [SKKU station SUMO]
echo   1. Simulation with cars and buses (default)
echo   2. Roads only
echo   3. Rebuild network, then simulate
echo.
choice /c 123 /n /t 10 /d 1 /m "Choose 1-3 (default 1 in 10 s): "
set "MODE=%ERRORLEVEL%"

:run
if "%MODE%"=="3" (
    python -X utf8 build.py --no-check || goto :fail
    set "MODE=1"
)
if "%MODE%"=="2" (
    start "" "%GUI%" -n skku.net.xml -a skku.add.xml,bus.stops.xml,bg.add.xml -g skku.gui.xml
) else (
    rem view_skku.py: sumo-gui + TraCI (lower-layer cars drawn translucent). Falls back to plain sumo-gui without Python
    python -X utf8 view_skku.py || start "" "%GUI%" -c skku.sumocfg --start
)
exit /b 0

:fail
echo.
echo Build failed. Check the error above.
pause
exit /b 1