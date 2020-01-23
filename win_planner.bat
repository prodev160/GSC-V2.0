cd %~dp0
CALL venv\Scripts\activate.bat

:loop

python planner.py

TIMEOUT /T 60

goto loop
