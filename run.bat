@echo off
rem Stock Eagle - kaynnistys. Avaa selaimeen http://localhost:8501
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Virtuaaliymparistoa ei loydy. Aja ensin setup.bat
    exit /b 1
)
.venv\Scripts\python.exe -m streamlit run app.py --server.headless false --browser.gatherUsageStats false
