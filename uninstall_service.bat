@echo off
:: ============================================
:: IPS Dashboard - Uninstall Windows Service
:: ============================================
:: Script ini harus dijalankan sebagai Administrator
:: ============================================

:: Check Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ============================================
    echo   ERROR: Jalankan script ini sebagai Administrator!
    echo   Klik kanan ^> Run as administrator
    echo ============================================
    echo.
    pause
    exit /b 1
)

:: Set variables
set SERVICE_NAME=IPS_Dashboard
set SCRIPT_DIR=%~dp0
set NSSM_PATH=%SCRIPT_DIR%nssm.exe

echo.
echo ============================================
echo   IPS Dashboard - Service Uninstaller
echo ============================================
echo.

:: Check nssm.exe exists
if not exist "%NSSM_PATH%" (
    echo [ERROR] nssm.exe tidak ditemukan di: %NSSM_PATH%
    pause
    exit /b 1
)

:: Check if service exists
sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Service "%SERVICE_NAME%" tidak ditemukan.
    echo Tidak ada yang perlu dihapus.
    echo.
    pause
    exit /b 0
)

:: Confirm uninstall
echo Anda akan menghapus service "%SERVICE_NAME%" dari sistem.
echo.
set /p CONFIRM=Apakah Anda yakin? (Y/N): 
if /I not "%CONFIRM%"=="Y" (
    echo Dibatalkan.
    pause
    exit /b 0
)

:: Stop the service
echo.
echo [1/2] Menghentikan service...
"%NSSM_PATH%" stop %SERVICE_NAME% >nul 2>&1
timeout /t 2 >nul

:: Remove the service
echo [2/2] Menghapus service...
"%NSSM_PATH%" remove %SERVICE_NAME% confirm
if %errorLevel% neq 0 (
    echo [ERROR] Gagal menghapus service!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   BERHASIL!
echo   Service "%SERVICE_NAME%" telah dihapus.
echo ============================================
echo.
pause
