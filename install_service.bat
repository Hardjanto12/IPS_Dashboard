@echo off
:: ============================================
:: IPS Dashboard - Install Windows Service
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
set EXE_PATH=%SCRIPT_DIR%backend\dist\BPM_API_Server.exe
set APP_DIR=%SCRIPT_DIR%backend\dist

echo.
echo ============================================
echo   IPS Dashboard - Service Installer
echo ============================================
echo.

:: Check nssm.exe exists
if not exist "%NSSM_PATH%" (
    echo [ERROR] nssm.exe tidak ditemukan di: %NSSM_PATH%
    echo Pastikan file nssm.exe berada di folder yang sama dengan script ini.
    pause
    exit /b 1
)

:: Check executable exists
if not exist "%EXE_PATH%" (
    echo [ERROR] BPM_API_Server.exe tidak ditemukan di: %EXE_PATH%
    echo Pastikan Anda sudah melakukan compile terlebih dahulu:
    echo   cd backend
    echo   pyinstaller BPM_API_Server.spec
    echo.
    pause
    exit /b 1
)

:: Check if service already exists
sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% equ 0 (
    echo [INFO] Service "%SERVICE_NAME%" sudah terinstall.
    echo Menghentikan service lama...
    "%NSSM_PATH%" stop %SERVICE_NAME% >nul 2>&1
    echo Menghapus service lama...
    "%NSSM_PATH%" remove %SERVICE_NAME% confirm >nul 2>&1
    timeout /t 2 >nul
)

:: Install service
echo [1/4] Menginstall service "%SERVICE_NAME%"...
"%NSSM_PATH%" install %SERVICE_NAME% "%EXE_PATH%"
if %errorLevel% neq 0 (
    echo [ERROR] Gagal menginstall service!
    pause
    exit /b 1
)

:: Configure working directory
echo [2/4] Mengatur working directory...
"%NSSM_PATH%" set %SERVICE_NAME% AppDirectory "%APP_DIR%"

:: Configure service to start automatically
echo [3/4] Mengatur startup otomatis...
"%NSSM_PATH%" set %SERVICE_NAME% Start SERVICE_AUTO_START

:: Configure service description
"%NSSM_PATH%" set %SERVICE_NAME% DisplayName "IPS Dashboard Server"
"%NSSM_PATH%" set %SERVICE_NAME% Description "Nuctech IPS Dashboard - Backend API and Frontend Web Server (Port 8000)"

:: Configure restart on failure
"%NSSM_PATH%" set %SERVICE_NAME% AppExit Default Restart
"%NSSM_PATH%" set %SERVICE_NAME% AppRestartDelay 5000

:: Start the service
echo [4/4] Menjalankan service...
"%NSSM_PATH%" start %SERVICE_NAME%
if %errorLevel% neq 0 (
    echo [WARNING] Service terinstall tapi gagal dijalankan.
    echo Coba jalankan manual di services.msc
) else (
    echo.
    echo ============================================
    echo   BERHASIL!
    echo ============================================
    echo   Service Name  : %SERVICE_NAME%
    echo   Executable    : %EXE_PATH%
    echo   Port          : 8000
    echo   Startup       : Automatic
    echo   Auto-Restart  : Ya (jika crash, restart setelah 5 detik)
    echo.
    echo   Akses dashboard di browser:
    echo   http://localhost:8000/dashboard
    echo.
    echo   Kelola service di: services.msc
    echo ============================================
)

echo.
pause
