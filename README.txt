# Prerequisites
- Python 3.x


# Manual deployment
## Windows
1. Go to src directory, create and activate virtual environment, and install dependencies:
	python.exe -m venv venv
	venv\Scripts\activate.bat
	pip3 install -r requirements.txt
2. Launch Python and initialize database:
	python.exe
	from gscontrol import db
	db.create_all()
	exit()

## Unix/Linux
1. Go to src directory, create and activate virtual environment, and install dependencies:
	python3 -m venv venv
	. venv/bin/activate
	pip3 install -r requirements.txt
2. Launch Python and initialize database:
	python3
	from gscontrol import db
	db.create_all()
	exit()


# Configuring scheduled tasks execution
## Unix/Linux
1. Edit path to src directory in planner.sh and allow script execution:
	nano planner.sh
	chmod +x planner.sh
2. Schedule script execution to every minute:
	crontab -e
	* * * * * /path/to/src/planner.sh
	crontab -l


# Launching application
## Windows
1. Go to src directory and activate virtual environment:
	venv\Scripts\activate.bat
2. Set enviroment variables and launch application:
	set FLASK_APP=gscontrol
	set FLASK_ENV=development
	flask run --host=0.0.0.0 --port=5000

## Unix/Linux
1. Go to src directory and activate virtual environment:
	. venv/bin/activate
2. Set enviroment variables and launch application:
	export FLASK_APP=gscontrol
	export FLASK_ENV=development
	flask run --host=0.0.0.0 --port=5000
