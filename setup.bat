@echo off
rem Stock Eagle - asennus Windowsille. Luo virtuaaliympariston .venv ja asentaa riippuvuudet.
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 goto :nouv
if not exist .venv\Scripts\python.exe (
    uv venv --python 3.13 .venv || goto :error
)
uv pip install --python .venv\Scripts\python.exe -r requirements.txt || goto :error
goto :done

:nouv
if exist .venv\Scripts\python.exe goto :pip
where py >nul 2>nul
if errorlevel 1 goto :python
py -3 -m venv .venv || goto :error
goto :pip
:python
python -m venv .venv || goto :error
:pip
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error

:done
if not exist .env copy .env.example .env >nul
echo.
echo Valmis. Kaynnista sovellus: run.bat
exit /b 0
:error
echo Asennus epaonnistui. Tarvitaan Python 3.11+ (python.org) tai uv.
exit /b 1
