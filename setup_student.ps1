# setup_student.ps1 - 生徒PC初期設定スクリプト（1回だけ実行）
# 管理者権限で実行してください

$ErrorActionPreference = "Stop"

Write-Host "=== 生徒PC初期設定 ===" -ForegroundColor Cyan
Write-Host ""

# --- PC番号の入力と確認 ---
$maxRetries = 3
$pcNumber = $null
for ($i = 0; $i -lt $maxRetries; $i++) {
    $input = Read-Host "このPCの番号を入力してください（01〜09、例: 01, 02, 03...）"

    # 入力チェック: 01〜09 の形式
    if ($input -match "^0[1-9]$") {
        $pcNumber = $input
        break
    } else {
        Write-Host "❌ 入力エラー: 01〜09 の形式で入力してください" -ForegroundColor Red
    }
}

if ($null -eq $pcNumber) {
    Write-Host "❌ 有効なPC番号が入力されませんでした。セットアップを中止します。" -ForegroundColor Red
    exit 1
}

$newComputerName = "PC-$pcNumber"
Write-Host "[OK] このPCを『$newComputerName』に設定します" -ForegroundColor Green
Write-Host ""

# --- .env の確認 ---
$envPath = "$PSScriptRoot\.env"
if (Test-Path $envPath) {
    Write-Host "[OK] .env を確認しました"
} else {
    Write-Warning ".env が見つかりません。先生PCで .env を作成してから再実行してください: $envPath"
}

# --- ポート 8080 のファイアウォール開放 ---
Write-Host "ポート 8080 (trigger_server) をファイアウォールで開放しています..."
Remove-NetFirewallRule -DisplayName "SchoolTriggerServer" -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName "SchoolTriggerServer" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 8080 `
    -Profile Any | Out-Null
Write-Host "[OK] ポート 8080 を開放しました（全プロファイル対象）"

# --- Python / pip の確認 ---
try {
    $pyVer = python --version 2>&1
    Write-Host "[OK] Python: $pyVer"
} catch {
    Write-Warning "Python が見つかりません。手動でインストールしてください。"
}

# --- selenium のインストール ---
Write-Host "selenium をインストールしています..."
pip install selenium --quiet
Write-Host "[OK] selenium のインストール完了"

# --- trigger_server.py をスタートアップフォルダに登録（VBS経由で非表示起動） ---
Write-Host "trigger_server.py をスタートアップに登録しています..."
$serverPath = "$PSScriptRoot\trigger_server.py"
$pythonwExe = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if ($null -eq $pythonwExe) {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($null -ne $pythonExe) {
        $pythonwExe = Join-Path (Split-Path $pythonExe) "pythonw.exe"
    }
}
if ($null -eq $pythonwExe -or -not (Test-Path $pythonwExe)) {
    Write-Warning "pythonw.exe が見つかりません。スタートアップ登録をスキップします。"
} else {
    $startupDir = [System.Environment]::GetFolderPath("Startup")
    $vbsPath = "$startupDir\SchoolTriggerServer.vbs"
    $vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """$pythonwExe"" ""$serverPath""", 0, False
"@
    Set-Content -Path $vbsPath -Value $vbsContent -Encoding UTF8
    Write-Host "[OK] スタートアップ登録: $vbsPath"

    # 今すぐ起動（既存プロセスを停止してから）
    Get-Process -Name "pythonw" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*trigger_server*" } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $pythonwExe -ArgumentList "`"$serverPath`"" -WindowStyle Hidden
    Start-Sleep -Seconds 2

    $listening = netstat -an 2>$null | Select-String ":8080"
    if ($listening) {
        Write-Host "[OK] trigger_server.py が起動しました（ポート 8080）" -ForegroundColor Green
    } else {
        Write-Warning "ポート 8080 が確認できません。再起動後に自動起動します。"
    }
}

# --- コンピュータ名の変更 ---
Write-Host "コンピュータ名を『$newComputerName』に変更しています..."
try {
    Rename-Computer -NewName $newComputerName -Force -ErrorAction Stop
    Write-Host "[OK] コンピュータ名を『$newComputerName』に変更しました" -ForegroundColor Green
    $rebootRequired = $true
} catch {
    Write-Host "[エラー] コンピュータ名の変更に失敗しました: $_" -ForegroundColor Red
    $rebootRequired = $false
}

Write-Host ""
Write-Host "=== 生徒PC初期設定が完了しました ===" -ForegroundColor Green
Write-Host "新しいコンピュータ名: $newComputerName"
Write-Host "プロジェクトフォルダ: $PSScriptRoot"
Write-Host ""

if ($rebootRequired) {
    Write-Host "⚠️  コンピュータ名の変更を有効にするため、再起動が必要です。" -ForegroundColor Yellow
    $reboot = Read-Host "今すぐ再起動しますか？（Y/n）"
    if ($reboot -ne "n") {
        Write-Host "30秒後に再起動します..."
        shutdown /r /t 30 /c "コンピュータ名変更のため再起動"
    }
}
