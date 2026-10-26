@echo off
title RemoDesk - Install to Connected Phone
echo ========================================================
echo        INSTALL REMODESK TO CONNECTED ANDROID PHONE
echo ========================================================
echo.
cd /d "%~dp0"

set "ADB=C:\platform-tools\adb.exe"
if not exist "%ADB%" (
    set "ADB=C:\Users\%USERNAME%\AppData\Local\Android\Sdk\platform-tools\adb.exe"
)
if not exist "%ADB%" (
    set "ADB=adb.exe"
)

echo Checking for connected Android phone via USB...
"%ADB%" devices

echo.
echo Installing RemoDesk-latest.apk to phone...
"%ADB%" install -r "Apk\RemoDesk-latest.apk"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] RemoDesk successfully installed on your Android phone!
    echo Launching RemoDesk on your phone now...
    "%ADB%" shell am start -n com.remodesk.client/.MainActivity
) else (
    echo.
    echo [NOTE] If installation failed, make sure:
    echo   1. Your phone is plugged in via USB.
    echo   2. "USB Debugging" is enabled in Developer Options on your phone.
    echo   3. You tap "Allow" on your phone's screen when prompted.
)

echo.
pause
