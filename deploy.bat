@echo off
REM Djobea AI Docker Deployment Script for Windows (Command Prompt)
REM Batch file wrapper for PowerShell script

setlocal

REM Check if PowerShell is available
where powershell >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: PowerShell is not available. Please install PowerShell.
    exit /b 1
)

REM Check if deploy.ps1 exists
if not exist "deploy.ps1" (
    echo ERROR: deploy.ps1 not found in current directory.
    exit /b 1
)

REM Execute PowerShell script with arguments
if "%~1"=="" (
    powershell -ExecutionPolicy Bypass -File "deploy.ps1" help
) else if "%~2"=="" (
    powershell -ExecutionPolicy Bypass -File "deploy.ps1" %1
) else (
    powershell -ExecutionPolicy Bypass -File "deploy.ps1" %1 %2
)

exit /b %errorlevel%