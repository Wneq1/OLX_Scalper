@echo off
echo Instalowanie wymaganych bibliotek...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Wystapil blad podczas instalacji. Sprawdz czy Python jest zainstalowany i dodany do PATH.
    pause
    exit /b 1
)
echo.
echo Instalacja zakonczona sukcesem!
echo Mozesz teraz uruchomic program za pomoca pliku run.bat
pause
