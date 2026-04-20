@echo off
cd /d "%~dp0..\frontend"
call npx vite --host 0.0.0.0 --port 5173
