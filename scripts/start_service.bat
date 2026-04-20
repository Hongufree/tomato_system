@echo off
cd /d "%~dp0.."
python_env\python.exe service\tomato_dl_merge_service.py
