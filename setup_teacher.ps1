# setup_teacher.ps1 - 先生PC初期設定スクリプト（1回だけ実行）
# 管理者権限で実行してください

$ErrorActionPreference = "Stop"

Write-Host "=== 先生PC初期設定 ===" -ForegroundColor Cyan

# --- lessons フォルダ作成（ユーザーディレクトリ以下） ---
$lessonsDir = "$env:USERPROFILE\AppData\Local\school\lessons"
if (-not (Test-Path $lessonsDir)) {
    New-Item -ItemType Directory -Path $lessonsDir | Out-Null
    Write-Host "[OK] $lessonsDir を作成しました"
} else {
    Write-Host "[SKIP] $lessonsDir は既に存在します"
}

# --- 共有設定 (Everyone 読み取り) ---
$shareName = "lessons"
$existingShare = Get-SmbShare -Name $shareName -ErrorAction SilentlyContinue
if ($null -eq $existingShare) {
    New-SmbShare -Name $shareName -Path $lessonsDir -ReadAccess "Everyone" | Out-Null
    Write-Host "[OK] 共有フォルダ \\$env:COMPUTERNAME\$shareName を作成しました"
} else {
    Write-Host "[SKIP] 共有 '$shareName' は既に存在します"
}

# --- WinRM を有効化（生徒PCへのリモート実行に必要） ---
Write-Host "WinRM を有効化しています..."
Enable-PSRemoting -Force | Out-Null
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
Write-Host "[OK] WinRM を有効化しました"

# --- Python / pip の確認 ---
try {
    $pyVer = python --version 2>&1
    Write-Host "[OK] Python: $pyVer"
} catch {
    Write-Warning "Python が見つかりません。teacher_app.py 実行に必要です。手動でインストールしてください。"
}

# --- tkinter は Python 標準同梱なので pip 不要 ---

# --- students.json をユーザーディレクトリにコピー（任意） ---
$jsonSrc = Join-Path $PSScriptRoot "students.json"
$schoolDir = "$env:USERPROFILE\AppData\Local\school"
if (-not (Test-Path $schoolDir)) {
    New-Item -ItemType Directory -Path $schoolDir | Out-Null
}
if (Test-Path $jsonSrc) {
    Copy-Item -Path $jsonSrc -Destination "$schoolDir\students.json" -Force
    Write-Host "[OK] students.json を $schoolDir にコピーしました"
}

Write-Host ""
Write-Host "次のステップ:"
Write-Host "  1. $lessonsDir に各生徒の .mkcd ファイルを配置してください"
Write-Host "  2. $schoolDir\students.json の内容（ログイン情報・ワールド名）を編集してください"
Write-Host "  3. teacher_app.py を実行してください: python teacher_app.py"
Write-Host ""
Write-Host "=== 先生PC初期設定が完了しました ===" -ForegroundColor Green
Write-Host "先生PCのコンピュータ名: $env:COMPUTERNAME"
Write-Host "(students.json の mkcd_share を \\\\$env:COMPUTERNAME\\lessons\\ に設定してください)"
