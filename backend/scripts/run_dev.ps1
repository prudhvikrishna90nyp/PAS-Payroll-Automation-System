Set-Location (Join-Path $PSScriptRoot "..")
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
