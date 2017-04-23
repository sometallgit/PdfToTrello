@ECHO OFF

cd /d %~dp0
"%~dp0Python\python.exe" "%~dp0readPdf.py" %* 
PAUSE