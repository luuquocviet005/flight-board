@echo off
rem Run dbt from the project venv with variables from ..\.env (e.g.  .\dbt build)
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%~dp0..\.env") do set "%%a=%%b"
set "DBT_PROFILES_DIR=%~dp0"
"%~dp0..\.venv\Scripts\dbt.exe" %*
