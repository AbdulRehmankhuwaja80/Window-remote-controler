# RemoDesk — Download & Installation Package Guide

This folder contains the complete, compressed packages for the RemoDesk Remote Desktop system.

---

## Package Directory (`Apk/`)

1. **`RemoDesk-Android-Client-Project.zip`**
   - Full native Kotlin Android project built with Jetpack Compose & WebRTC Android SDK.
   - Ready to open directly in Android Studio.
   - Supports touch gestures (tap, double-tap, long-press right-click, two-finger scroll, pinch zoom), virtual touchpad mode, on-screen Windows modifier keys, file management, and biometric authentication.

2. **`RemoDesk-Windows-Host-Agent.zip`**
   - Windows 10/11 Host Agent.
   - Contains:
     - The compiled C# .NET 8 WinForms binary (`bin/Debug/net8.0-windows10.0.19041.0/RemoDesk.Host.dll`) with tray icon, active session indicators, DXGI desktop duplication capturer, and Win32 `SendInput` input injector.
     - The native Win32 Python standalone host agent (`windows-host/python-host/host_agent.py`).
     - Automated test scripts.

3. **`RemoDesk-Backend-And-Deploy.zip`**
   - Cloud signaling and authentication server built on Python FastAPI, WebSockets, and async SQLAlchemy.
   - Coturn STUN/TURN server configuration (`turnserver.conf`) for NAT traversal across disparate networks.
   - Nginx reverse proxy configuration and Docker Compose setup for 1-click cloud deployment.

4. **`RemoDesk-Complete-Suite.zip`**
   - The master all-in-one distribution bundle containing the Android mobile client, Windows host agent, cloud gateway, Docker files, and technical documentation.

---

## Quick Start: How to Run & Connect

### 1. Run the Gateway Server
From the root folder, run:
```cmd
.\scripts\run_backend.bat
```
*(Interactive API documentation is accessible at `http://127.0.0.1:8000/docs`)*

### 2. Start the Windows Laptop Host
From the root folder, run:
```cmd
.\scripts\run_host_csharp.bat
```
*(Or run `.\scripts\run_host_python.bat`)*. The laptop will register with the gateway and show the host control panel with a green Online status.

### 3. Build & Install Android Client
1. Extract `RemoDesk-Android-Client-Project.zip`.
2. Open the folder in **Android Studio**.
3. Select **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
4. Install the generated APK on your Android smartphone (`adb install app-debug.apk` or copy via USB).
5. Open the app, register your account, and tap **Connect** to control your Windows laptop!
