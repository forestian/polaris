@echo off
echo PyInstaller 설치 확인...
python -m pip install pyinstaller -q
echo.

REM build.py 가 버전 동기화 가드 + 클린 + 빌드 + 검증을 모두 수행
python build.py %*
if errorlevel 1 (
    echo.
    echo [실패] 위 메시지를 확인하세요.
    pause
    exit /b 1
)

echo.
echo 완료! dist\Polaris.exe 를 실행하세요.
pause
