# setup_student.ps1 - 生徒PC初期設定スクリプト（1回だけ実行）
# 管理者権限で実行してください

$ErrorActionPreference = "Stop"

Write-Host "=== 生徒PC初期設定 ===" -ForegroundColor Cyan

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

Write-Host ""
Write-Host "=== 生徒PC初期設定が完了しました ===" -ForegroundColor Green
Write-Host "このPCのコンピュータ名: $env:COMPUTERNAME"
