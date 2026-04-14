# build.ps1 - EXEビルドスクリプト（ビルド環境のみで実行）
# 実行: Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force; .\build.ps1
#
# 出力:
#   dist\teacher\teacher_app.exe        先生PC用
#   dist\student\trigger_server.exe     生徒PC用（常駐サーバー）
#   dist\student\agent.exe              生徒PC用（ブラウザ操作）

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host "=== EXEビルド開始 ===" -ForegroundColor Cyan

# --- PyInstaller の確認・インストール ---
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller をインストールしています..."
    pip install pyinstaller
}

# --- 出力ディレクトリの準備 ---
$DistTeacher  = "$Root\dist\teacher"
$DistStudent  = "$Root\dist\student"
$WorkDir      = "$Root\build_tmp"
foreach ($d in @($DistTeacher, $DistStudent, $WorkDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

# --- 共通 PyInstaller オプション ---
$CommonArgs = @(
    "--onefile",
    "--distpath", $WorkDir,
    "--workpath", "$Root\pyinstaller_work",
    "--specpath", "$Root\pyinstaller_work"
)

# --- 1. teacher_app.exe（GUIアプリ・コンソール非表示） ---
Write-Host ""
Write-Host "[1/3] teacher_app.exe をビルドしています..." -ForegroundColor Yellow
pyinstaller @CommonArgs `
    --noconsole `
    --name teacher_app `
    "$Root\teacher_app.py"

Copy-Item "$WorkDir\teacher_app.exe" -Destination $DistTeacher -Force
Write-Host "[OK] $DistTeacher\teacher_app.exe" -ForegroundColor Green

# --- 2. trigger_server.exe（常駐サーバー・コンソール非表示） ---
Write-Host ""
Write-Host "[2/3] trigger_server.exe をビルドしています..." -ForegroundColor Yellow
pyinstaller @CommonArgs `
    --noconsole `
    --name trigger_server `
    "$Root\trigger_server.py"

Copy-Item "$WorkDir\trigger_server.exe" -Destination $DistStudent -Force
Write-Host "[OK] $DistStudent\trigger_server.exe" -ForegroundColor Green

# --- 3. agent.exe（Selenium同梱・コンソールあり） ---
Write-Host ""
Write-Host "[3/3] agent.exe をビルドしています..." -ForegroundColor Yellow
pyinstaller @CommonArgs `
    --console `
    --name agent `
    --collect-all selenium `
    "$Root\agent.py"

Copy-Item "$WorkDir\agent.exe" -Destination $DistStudent -Force
Write-Host "[OK] $DistStudent\agent.exe" -ForegroundColor Green

# --- 配布に必要な設定ファイルをコピー ---
Write-Host ""
Write-Host "設定ファイルをコピーしています..."

# 先生PC用
Copy-Item "$Root\students.json"     -Destination $DistTeacher -Force
Copy-Item "$Root\mkcd_map.json"     -Destination $DistTeacher -Force
Copy-Item "$Root\.env.example"      -Destination $DistTeacher -Force
Copy-Item "$Root\setup_teacher.ps1" -Destination $DistTeacher -Force

# 生徒PC用
Copy-Item "$Root\.env.example"      -Destination $DistStudent -Force
Copy-Item "$Root\setup_student.ps1" -Destination $DistStudent -Force

# --- 一時ファイルの削除 ---
Remove-Item $WorkDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$Root\pyinstaller_work" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== ビルド完了 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "配布物:"
Write-Host "  先生PC用: $DistTeacher\"
Write-Host "    teacher_app.exe / students.json / mkcd_map.json / .env.example / setup_teacher.ps1"
Write-Host ""
Write-Host "  生徒PC用: $DistStudent\"
Write-Host "    trigger_server.exe / agent.exe / .env.example / setup_student.ps1"
Write-Host ""
Write-Host "注意: .env は .env.example をコピーして TRIGGER_TOKEN を設定してから配布してください"
