@echo off
title RemoDesk - Push to GitHub Collab Repo
echo ========================================================
echo        PUSHING UPDATES TO GITHUB COLLAB REPO
echo ========================================================
echo.
cd /d "%~dp0"

echo Target Repository : https://github.com/AbdulRehmankhuwaja80/Window-remote-controler.git
echo Target Branch     : main
echo.
echo Pushing commit directly onto main...
git push origin main

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo SUCCESS! All updates have been merged and pushed to main!
    echo ========================================================
) else (
    echo [NOTE] If you were prompted for GitHub authentication, please authorize.
)
echo.
pause
