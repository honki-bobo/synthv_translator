@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   SynthV Translator - Windows Installer
echo ============================================
echo.

:: -----------------------------------------------
:: Step 1: Check / Install Python
:: -----------------------------------------------
echo [Step 1/5] Checking for Python...

python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   Found: %%v
    goto :python_done
)

echo   Python not found. Downloading installer...
echo.

:: Update this URL when a newer Python version is released.
:: Find the latest at https://www.python.org/downloads/
set "PYTHON_URL=https://www.python.org/ftp/python/3.14.3/python-3.14.3-amd64.exe"

powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%TEMP%\python-installer.exe'"
if %errorlevel% neq 0 (
    echo   ERROR: Failed to download Python installer.
    echo   Please download and install Python manually from https://www.python.org/downloads/
    goto :python_done
)

echo   Starting Python installer...
echo   IMPORTANT: Make sure to check "Add Python to PATH" in the installer!
echo.
start /wait "" "%TEMP%\python-installer.exe"

echo.
echo   Press any key after the Python installer has finished...
pause >nul

:: Refresh PATH for this session
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USER_PATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%B"
set "PATH=%SYS_PATH%;%USER_PATH%"

python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   Python installed: %%v
) else (
    echo   WARNING: Python still not found on PATH.
    echo   You may need to close and reopen this script after installing Python.
)

:python_done
echo.

:: -----------------------------------------------
:: Step 2: Check / Install eSpeak NG
:: -----------------------------------------------
echo [Step 2/5] Checking for eSpeak NG...

set "ESPEAK_EXE=C:\Program Files\eSpeak NG\espeak-ng.exe"
set "ESPEAK_DLL=C:\Program Files\eSpeak NG\libespeak-ng.dll"

if exist "%ESPEAK_EXE%" (
    echo   Found: eSpeak NG at %ESPEAK_EXE%
    goto :espeak_done
)

where espeak-ng >nul 2>&1
if %errorlevel% equ 0 (
    echo   Found: eSpeak NG on PATH
    goto :espeak_done
)

echo   eSpeak NG not found. Fetching latest release from GitHub...
echo.

:: Query GitHub API for latest release MSI URL
for /f "tokens=*" %%u in ('powershell -Command "try { (Invoke-RestMethod -Uri 'https://api.github.com/repos/espeak-ng/espeak-ng/releases/latest').assets | Where-Object { $_.name -like '*.msi' } | Select-Object -First 1 -ExpandProperty browser_download_url } catch { Write-Host 'ERROR' }"') do set "ESPEAK_URL=%%u"

if "%ESPEAK_URL%"=="ERROR" (
    echo   ERROR: Failed to fetch eSpeak NG release info from GitHub.
    echo   Please download and install eSpeak NG manually from:
    echo   https://github.com/espeak-ng/espeak-ng/releases
    goto :espeak_done
)
if "%ESPEAK_URL%"=="" (
    echo   ERROR: Could not find eSpeak NG MSI in latest release.
    echo   Please download and install eSpeak NG manually from:
    echo   https://github.com/espeak-ng/espeak-ng/releases
    goto :espeak_done
)

echo   Downloading from: %ESPEAK_URL%
powershell -Command "Invoke-WebRequest -Uri '%ESPEAK_URL%' -OutFile '%TEMP%\espeak-ng.msi'"
if %errorlevel% neq 0 (
    echo   ERROR: Failed to download eSpeak NG installer.
    echo   Please download and install eSpeak NG manually from:
    echo   https://github.com/espeak-ng/espeak-ng/releases
    goto :espeak_done
)

echo   Starting eSpeak NG installer...
echo.
msiexec /i "%TEMP%\espeak-ng.msi"

echo.
echo   Press any key after the eSpeak NG installer has finished...
pause >nul

if exist "%ESPEAK_EXE%" (
    echo   eSpeak NG installed successfully.
) else (
    echo   WARNING: eSpeak NG not found at expected location.
    echo   If you installed to a custom directory, set the environment variables manually.
)

:espeak_done
echo.

:: -----------------------------------------------
:: Step 3: Set environment variables for eSpeak NG
:: -----------------------------------------------
echo [Step 3/5] Setting eSpeak NG environment variables...

if exist "%ESPEAK_EXE%" (
    setx PHONEMIZER_ESPEAK_PATH "%ESPEAK_EXE%" >nul 2>&1
    set "PHONEMIZER_ESPEAK_PATH=%ESPEAK_EXE%"
    echo   PHONEMIZER_ESPEAK_PATH = %ESPEAK_EXE%
) else (
    echo   Skipped: eSpeak NG executable not found at default location.
)

if exist "%ESPEAK_DLL%" (
    setx PHONEMIZER_ESPEAK_LIBRARY "%ESPEAK_DLL%" >nul 2>&1
    set "PHONEMIZER_ESPEAK_LIBRARY=%ESPEAK_DLL%"
    echo   PHONEMIZER_ESPEAK_LIBRARY = %ESPEAK_DLL%
) else (
    echo   Skipped: eSpeak NG library not found at default location.
)

echo.

:: -----------------------------------------------
:: Step 4: Install Python dependencies
:: -----------------------------------------------
echo [Step 4/5] Installing Python dependencies...

pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo   WARNING: pip install failed. You can retry manually with:
    echo   pip install -r requirements.txt
)

echo.

:: -----------------------------------------------
:: Step 5: Copy inserter script to SynthV
:: -----------------------------------------------
echo [Step 5/5] Copying inserter script to Synthesizer V...

set "SYNTHV_SCRIPTS=%APPDATA%\Dreamtonics\Synthesizer V Studio 2\scripts"
set "INSERTER_SRC=%~dp0synthv_translator_inserter.js"

if not exist "%INSERTER_SRC%" (
    echo   WARNING: synthv_translator_inserter.js not found in project directory.
    echo   Skipping this step.
    goto :copy_done
)

if exist "%SYNTHV_SCRIPTS%" (
    copy /y "%INSERTER_SRC%" "%SYNTHV_SCRIPTS%\" >nul
    echo   Copied to: %SYNTHV_SCRIPTS%
    echo   Open Synthesizer V and go to Scripts ^> Rescan to load the script.
) else (
    echo   Synthesizer V scripts folder not found at:
    echo   %SYNTHV_SCRIPTS%
    echo.
    echo   If Synthesizer V is installed, you can find the scripts folder by
    echo   opening Synthesizer V and going to Scripts ^> Open Scripts Folder.
    echo   Then copy synthv_translator_inserter.js there manually.
)

:copy_done
echo.

:: -----------------------------------------------
:: Done
:: -----------------------------------------------
echo ============================================
echo   Installation complete!
echo ============================================
echo.
echo   To test the translator, run:
echo   python synthv_translator.py "Hallo Welt"
echo.
pause
