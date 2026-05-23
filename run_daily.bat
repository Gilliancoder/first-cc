@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Daily Market Sense - Daily Update
echo   %date% %time%
echo ============================================

echo.
echo [1/3] Running pipeline (fetch + AI)...
:: Set UTF-8 for Python
set PYTHONIOENCODING=utf-8
D:\anaconda\python.exe pipeline\pipeline.py --date %date:~0,10%

echo.
echo [2/3] Building static site...
call npm run build 2>nul
:: npm build cleanup step often fails on Windows, manually copy files
D:\anaconda\python.exe -c "import os,shutil;src='.next/server/app';dst='out';[exec('p=os.path.join(r,f);t=os.path.join(dst,os.path.relpath(r,src),f);os.makedirs(os.path.dirname(t),exist_ok=True);shutil.copy2(p,t)')for r,_,fs in os.walk(src)for f in fs if f.endswith('.html')];shutil.copytree('.next/static','out/_next/static',dirs_exist_ok=True)if os.path.exists('.next/static')else None;[shutil.copy2(os.path.join('public',f),os.path.join('out',f))for f in os.listdir('public')if os.path.isfile(os.path.join('public',f))];print('Static site built')"

echo.
echo [3/3] Restarting server...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul
set PYTHONIOENCODING=utf-8
start "DailyMarketSense" D:\anaconda\python.exe server.py

echo.
echo Done! App available at:
echo   http://localhost:3000
echo.
