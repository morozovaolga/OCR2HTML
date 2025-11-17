# Скрипт для запуска ollama_check.py в фоне на Windows
# Использование: .\run_ollama_background.ps1

param(
    [string]$InputFile = "out/final_better.txt",
    [string]$OutputDir = "out",
    [string]$Title = "Документ (Ollama)",
    [string]$Model = "mistral:latest",
    [int]$Timeout = 300,
    [string]$LogFile = "out/ollama_log.txt"
)

# Создаем файл для запуска
$scriptContent = @"
python ollama_check.py --in "$InputFile" --outdir "$OutputDir" --title "$Title" --model "$Model" --timeout $Timeout --log-file "$LogFile"
"@

# Запускаем в новом окне PowerShell
Start-Process powershell -ArgumentList "-NoExit", "-Command", $scriptContent

Write-Host "Скрипт запущен в отдельном окне PowerShell."
Write-Host "Логи сохраняются в: $LogFile"
Write-Host "Окно PowerShell останется открытым, чтобы процесс продолжал работать."
Write-Host ""
Write-Host "ВАЖНО: Компьютер НЕ должен переходить в спящий режим, иначе процесс остановится."
Write-Host "Чтобы предотвратить спящий режим, выполните:"
Write-Host "  powercfg /change standby-timeout-ac 0"
Write-Host "  powercfg /change standby-timeout-dc 0"

