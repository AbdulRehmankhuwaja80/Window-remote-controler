@echo off
:: RemoDesk Firewall Port Opener (Runs as Administrator)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Requesting Administrator privileges to configure Windows Firewall...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo Configuring Windows Defender Firewall for RemoDesk...
echo ========================================================

netsh advfirewall firewall delete rule name="RemoDesk Gateway (Port 8000)" >nul 2>&1
netsh advfirewall firewall add rule name="RemoDesk Gateway (Port 8000)" dir=in action=allow protocol=TCP localport=8000 profile=any

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo SUCCESS! Port 8000 is now OPEN in Windows Firewall.
    echo Your Android phone can now connect to:
    echo http://192.168.0.44:8000
    echo ========================================================
) else (
    echo [ERROR] Failed to add firewall rule.
)
echo.
pause
