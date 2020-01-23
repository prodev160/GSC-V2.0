python -m venv venv
CALL venv\Scripts\activate.bat
pip install -r requirements.txt
python -c "from gscontrol import db; db.create_all()"
