@echo off
setlocal
cd /d "%~dp0"

set PY=E:\python\python.exe

echo ==========================================
echo   FBPet one-click build (onefile)
echo ==========================================
echo.

if not exist "%PY%" (
    echo [ERROR] Python not found: %PY%
    echo         Edit build.bat and set PY to your Python path.
    goto :fail
)

"%PY%" -c "import tkinter" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] This Python has no tkinter: %PY%
    echo         Use a full Python install with tcl/tk enabled.
    goto :fail
)

echo [1/4] Installing dependencies ...
"%PY%" -m pip install -r requirements.txt || goto :fail
"%PY%" -m pip install pyinstaller || goto :fail

echo [2/4] Cleaning old build output ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/4] Building, first run may take a while ...
"%PY%" -m PyInstaller --noconfirm FBPet.spec || goto :fail

echo [4/4] Copying runtime resources beside the exe ...
copy /y config.json dist\ >nul || goto :fail
xcopy /e /i /y sprites dist\sprites >nul || goto :fail
xcopy /e /i /y audio dist\audio >nul || goto :fail

echo Done.
echo.
echo Output: dist\FBPet.exe
echo Resources (config.json, sprites, audio) are auto-copied beside the exe.
goto :done

:fail
echo.
echo [ERROR] Build failed, check the output above.
:done
echo.
pause
endlocal
