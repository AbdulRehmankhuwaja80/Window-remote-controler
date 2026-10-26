@echo off
title RemoDesk - Launch Phone Emulator
echo ========================================================
echo          REMODESK ANDROID PHONE EMULATOR LAUNCHER
echo ========================================================
echo.
cd /d "%~dp0"

set "EMU=C:\Users\%USERNAME%\AppData\Local\Android\Sdk\emulator\emulator.exe"
if not exist "%EMU%" (
    set "EMU=emulator.exe"
)

set "ADB=C:\platform-tools\adb.exe"
if not exist "%ADB%" (
    set "ADB=C:\Users\%USERNAME%\AppData\Local\Android\Sdk\platform-tools\adb.exe"
)
if not exist "%ADB%" (
    set "ADB=adb.exe"
)

echo [1/4] Starting Android Phone Emulator (Medium_Phone_API_37.0)...
start "" "%EMU%" -avd Medium_Phone_API_37.0 -netdelay none -netspeed full

echo [2/4] Waiting for Android Emulator to boot up...
"%ADB%" wait-for-device

echo [3/4] Installing RemoDesk APK on Emulator...
"%ADB%" install -r "Apk\RemoDesk-latest.apk"

echo [4/4] Launching RemoDesk Mobile Application...
"%ADB%" shell am start -n com.remodesk.client/.MainActivity

echo.
echo ========================================================
echo RemoDesk Phone App is now RUNNING on the emulator screen!
echo Note: When signing in on the emulator, use:
echo       Cloud Gateway URL: http://10.0.2.2:8000
echo ========================================================
pause
