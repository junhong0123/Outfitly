@echo off
echo Setting up AI Engine Environment...

REM Check if venv exists
IF NOT EXIST "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip and install requirements
echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing requirements...
pip install -r requirements.txt

echo Setup complete! To activate the environment, run:
echo call AI_Engine\venv\Scripts\activate.bat
echo To start Jupyter, run:
echo jupyter notebook
pause
