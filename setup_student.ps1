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

# --- WinRM (PowerShell Remoting) を有効化 ---
Write-Host "WinRM を有効化しています..."
Enable-PSRemoting -Force | Out-Null
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
Write-Host "[OK] WinRM を有効化しました"

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
