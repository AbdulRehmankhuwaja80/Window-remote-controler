# RemoDesk — Windows Host Agent Packaging Script
# Publishes RemoDesk.Host and compiles an Inno Setup installer or portable package.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$HostProj = Join-Path $ProjectRoot "windows-host\RemoDesk.Host\RemoDesk.Host.csproj"
$IssFile = Join-Path $ProjectRoot "windows-host\installer\RemoDesk_Host_Setup.iss"
$DistDir = Join-Path $ProjectRoot "dist"
$InstallerDir = Join-Path $DistDir "installer"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  RemoDesk Host Agent Packaging Pipeline                  " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Locate dotnet executable
$UserDotnet = Join-Path $env:USERPROFILE ".dotnet\dotnet.exe"
if (Test-Path $UserDotnet) {
    $Dotnet = $UserDotnet
} elseif (Get-Command "dotnet" -ErrorAction SilentlyContinue) {
    $Dotnet = "dotnet"
} else {
    Write-Error ".NET SDK not found. Please ensure .NET 8.0 SDK is installed."
    exit 1
}

Write-Host "[1/3] Publishing RemoDesk Host (Release win-x64)..." -ForegroundColor Yellow
$PublishDir = Join-Path $ProjectRoot "windows-host\RemoDesk.Host\bin\Release\net8.0-windows10.0.19041.0\publish\win-x64"

& $Dotnet publish $HostProj -c Release -r win-x64 --self-contained false -o $PublishDir
if ($LASTEXITCODE -ne 0) {
    Write-Error "dotnet publish failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "Publish succeeded: $PublishDir" -ForegroundColor Green

# 2. Ensure dist directories
if (-not (Test-Path $InstallerDir)) {
    New-Item -ItemType Directory -Force -Path $InstallerDir | Out-Null
}

# 3. Create portable zip
Write-Host "[2/3] Creating portable ZIP archive..." -ForegroundColor Yellow
$ZipFile = Join-Path $DistDir "RemoDesk_Host_Portable_v1.0.0.zip"
if (Test-Path $ZipFile) { Remove-Item $ZipFile -Force }
Compress-Archive -Path "$PublishDir\*" -DestinationPath $ZipFile -Force
Write-Host "Portable package created at: $ZipFile" -ForegroundColor Green

# 4. Check for Inno Setup compiler
Write-Host "[3/3] Checking for Inno Setup compiler (ISCC)..." -ForegroundColor Yellow
$IsccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "ISCC.exe"
)

$IsccPath = $null
foreach ($c in $IsccCandidates) {
    if (Test-Path $c -ErrorAction SilentlyContinue) {
        $IsccPath = $c
        break
    } elseif (Get-Command $c -ErrorAction SilentlyContinue) {
        $IsccPath = $c
        break
    }
}

if ($IsccPath) {
    Write-Host "Found Inno Setup at $IsccPath. Compiling Windows Installer..." -ForegroundColor Green
    & $IsccPath $IssFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Installer successfully built in: $InstallerDir" -ForegroundColor Green
    } else {
        Write-Warning "Inno Setup compilation exited with code $LASTEXITCODE."
    }
} else {
    Write-Host "Inno Setup compiler not found in standard paths." -ForegroundColor DarkYellow
    Write-Host "To generate the single-file installer (.exe), install Inno Setup 6 from https://jrsoftware.org/isinfo.php" -ForegroundColor DarkYellow
    Write-Host "The portable package is ready for deployment at: $ZipFile" -ForegroundColor Cyan
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Packaging complete!                                      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
