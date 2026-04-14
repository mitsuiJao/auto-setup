# setup_teacher.ps1 - 先生PC初期設定スクリプト（1回だけ実行）
# 管理者権限で実行してください

$ErrorActionPreference = "Stop"

Write-Host "=== 先生PC初期設定 ===" -ForegroundColor Cyan

# --- lessons フォルダ作成（プロジェクトフォルダ以下） ---
$lessonsDir = "$PSScriptRoot\lessons"
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

# --- Python / pip の確認 ---
try {
    $pyVer = python --version 2>&1
    Write-Host "[OK] Python: $pyVer"
} catch {
    Write-Warning "Python が見つかりません。teacher_app.py 実行に必要です。手動でインストールしてください。"
}

# --- .env の確認 ---
$envPath = "$PSScriptRoot\.env"
if (Test-Path $envPath) {
    Write-Host "[OK] .env を確認しました"
} else {
    Write-Warning ".env が見つかりません。"
    Write-Warning ".env.example をコピーして .env を作成し、TRIGGER_TOKEN を設定してください。"
    Write-Warning "  例: TRIGGER_TOKEN=your_secret_token_here"
}

Write-Host ""
Write-Host "次のステップ:"
Write-Host "  1. .env ファイルを作成して TRIGGER_TOKEN に任意のトークンを設定してください"
Write-Host "     例: TRIGGER_TOKEN=your_secret_token_here"
Write-Host "  2. $lessonsDir に各生徒の .mkcd ファイルを配置してください"
Write-Host "  3. $PSScriptRoot\students.json の内容（ログイン情報・ワールド名）を編集してください"
Write-Host "  4. 生徒PCで setup_student.ps1 を実行してください（.env も一緒に配布されます）"
Write-Host "  5. teacher_app.py を実行してください: python `"$PSScriptRoot\teacher_app.py`""
Write-Host ""
Write-Host "=== 先生PC初期設定が完了しました ===" -ForegroundColor Green
Write-Host "先生PCのコンピュータ名: $env:COMPUTERNAME"
Write-Host "(students.json の mkcd_share を \\\\$env:COMPUTERNAME\\lessons\\ に設定してください)"
