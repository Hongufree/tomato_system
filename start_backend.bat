@echo off
cd /d "%~dp0..\backend"
call mvnw.cmd spring-boot:run
