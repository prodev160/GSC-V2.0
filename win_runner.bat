cd %~dp0
CALL venv\Scripts\activate.bat
set FLASK_APP=gscontrol
set FLASK_ENV=development
flask run
