@echo off
REM Скрипт для запуска ollama_check.py в фоне на Windows
REM Использование: run_ollama_background.bat

set INPUT_FILE=out/final_better.txt
set OUTPUT_DIR=out
set TITLE=Документ (Ollama)
set MODEL=mistral:latest
set TIMEOUT=300
set LOG_FILE=out/ollama_log.txt

REM Запускаем в новом окне
start "Ollama Check" cmd /k "python ollama_check.py --in %INPUT_FILE% --outdir %OUTPUT_DIR% --title %TITLE% --model %MODEL% --timeout %TIMEOUT% --log-file %LOG_FILE%"

echo Скрипт запущен в отдельном окне.
echo Логи сохраняются в: %LOG_FILE%
echo.
echo ВАЖНО: Компьютер НЕ должен переходить в спящий режим!
echo Чтобы предотвратить спящий режим, выполните:
echo   powercfg /change standby-timeout-ac 0
echo   powercfg /change standby-timeout-dc 0

