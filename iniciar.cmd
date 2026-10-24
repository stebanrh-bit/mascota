@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto dependencies
where py >nul 2>&1
if errorlevel 1 goto missing_python
py -3.12 -m venv .venv
if errorlevel 1 goto missing_python
:dependencies
".venv\Scripts\python.exe" -c "from importlib.metadata import version; assert version('PySide6') == '6.9.3'" >nul 2>&1
if not errorlevel 1 goto launch
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:launch
".venv\Scripts\python.exe" -m mascota
if errorlevel 1 goto failed
exit /b 0
:missing_python
echo Instala Python 3.12 de https://www.python.org/downloads/windows/
echo Activa el lanzador de Python durante la instalacion y vuelve a abrir iniciar.cmd.
pause
exit /b 1
:failed
echo No se pudo iniciar Mascota. Conserva el mensaje de error que aparece arriba.
pause
exit /b 1
