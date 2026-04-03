@echo off
echo Starting EduDesk Application...
echo.
echo Make sure you have run "python -m venv venv" and installed requirements initially!
echo.
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found. Running with global python.
)
python app.py
pause
