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

# --- ユーザーディレクトリ以下に school フォルダ作成 ---
$schoolDir = "$env:USERPROFILE\AppData\Local\school"
if (-not (Test-Path $schoolDir)) {
    New-Item -ItemType Directory -Path $schoolDir | Out-Null
    Write-Host "[OK] $schoolDir を作成しました"
} else {
    Write-Host "[SKIP] $schoolDir は既に存在します"
}

# --- agent.py をコピー ---
$agentSrc = Join-Path $PSScriptRoot "agent.py"
$agentDst = "$schoolDir\agent.py"
if (Test-Path $agentSrc) {
    Copy-Item -Path $agentSrc -Destination $agentDst -Force
    Write-Host "[OK] agent.py を $agentDst にコピーしました"
} else {
    Write-Warning "agent.py が見つかりません: $agentSrc"
}

# --- trigger_server.py をコピー ---
$serverSrc = Join-Path $PSScriptRoot "trigger_server.py"
$serverDst = "$schoolDir\trigger_server.py"
if (Test-Path $serverSrc) {
    Copy-Item -Path $serverSrc -Destination $serverDst -Force
    Write-Host "[OK] trigger_server.py を $serverDst にコピーしました"
} else {
    Write-Warning "trigger_server.py が見つかりません: $serverSrc"
}

# --- .env をコピー（TRIGGER_TOKEN を生徒PCにも配布） ---
$envSrc = Join-Path $PSScriptRoot ".env"
$envDst = "$schoolDir\.env"
if (Test-Path $envSrc) {
    Copy-Item -Path $envSrc -Destination $envDst -Force
    Write-Host "[OK] .env を $envDst にコピーしました"
} else {
    Write-Warning ".env が見つかりません。先生PCで .env を作成してから再実行してください: $envSrc"
}

# --- ポート 8080 のファイアウォール開放 ---
Write-Host "ポート 8080 (trigger_server) をファイアウォールで開放しています..."
netsh advfirewall firewall add rule `
    name="SchoolTriggerServer" `
    dir=in `
    action=allow `
    protocol=TCP `
    localport=8080 | Out-Null
Write-Host "[OK] ポート 8080 を開放しました"

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

# --- trigger_server.py をログオン時自動起動タスクに登録 ---
Write-Host "trigger_server.py をスタートアップタスクに登録しています..."
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($null -eq $pythonExe) {
    Write-Warning "python.exe が見つかりません。タスク登録をスキップします。"
} else {
    $taskCmd = "`"$pythonExe`" `"$serverDst`""
    schtasks /create `
        /tn "SchoolTriggerServer" `
        /tr $taskCmd `
        /sc onlogon `
        /ru $env:USERNAME `
        /it /f | Out-Null
    Write-Host "[OK] スタートアップタスク 'SchoolTriggerServer' を登録しました"

    # 今すぐ起動
    schtasks /run /tn "SchoolTriggerServer" | Out-Null
    Write-Host "[OK] trigger_server.py を起動しました（ポート 8080）"
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
Write-Host ""

if ($rebootRequired) {
    Write-Host "⚠️  コンピュータ名の変更を有効にするため、再起動が必要です。" -ForegroundColor Yellow
    $reboot = Read-Host "今すぐ再起動しますか？（Y/n）"
    if ($reboot -ne "n") {
        Write-Host "30秒後に再起動します..."
        shutdown /r /t 30 /c "コンピュータ名変更のため再起動"
    }
}
