@echo off
cd /d "C:\Users\ADN\Videos\Nouveau dossier (4)\dist"
SolidariteEtoile.exe > exe_log.txt 2>&1
type exe_log.txt
pause
