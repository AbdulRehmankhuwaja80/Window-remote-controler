@echo off
title RemoDesk - Build Android APK
echo ========================================================
echo            RemoDesk Android APK Builder
echo ========================================================
echo.

cd /d "%~dp0android-client"

echo [1/2] Building Android APK with Gradle Wrapper...
call gradlew.bat assembleDebug

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo [2/2] BUILD SUCCESSFUL!
    echo ========================================================
    if not exist "%~dp0Apk" mkdir "%~dp0Apk"
    copy /Y "%~dp0android-client\app\build\outputs\apk\debug\app-debug.apk" "%~dp0Apk\RemoDesk-latest.apk"
    echo.
    echo Fresh APK copied to:
    echo   %~dp0Apk\RemoDesk-latest.apk
    echo.
) else (
    echo.
    echo [ERROR] Gradle build failed. Check the error log above.
    echo.
)

pause
