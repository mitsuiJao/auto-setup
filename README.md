# 塾PC管理ツール

## 概要

先生PCのGUIアプリから、生徒PC全台に対してブラウザ自動操作（Selenium）を一括起動するツールです。

```
先生PC: teacher_app.py
    │  HTTP POST /start（ポート 8080）
    ▼
生徒PC: trigger_server.py（常駐）
    │
    └──▶ agent.py（Selenium でログイン・ワールド起動）
```

---

## ファイル構成

| ファイル | 説明 |
|---|---|
| `teacher_app.py` | 先生PC用GUIアプリ |
| `agent.py` | 生徒PCで動くブラウザ自動操作スクリプト |
| `trigger_server.py` | 生徒PC常駐HTTPサーバー（port 8080） |
| `students.json` | 生徒データ・設定 |
| `mkcd_map.json` | ワールド名の表示名↔ファイル名対応表 |
| `.env` | 認証トークン（gitignore済み・要作成） |
| `.env.example` | `.env` のテンプレート |
| `setup_teacher.ps1` | 先生PC初期設定（1回だけ実行） |
| `setup_student.ps1` | 生徒PC初期設定（1回だけ実行） |

---

## セットアップ手順

### 前提条件（全台共通）

- Windows 10 / 11、全台同一LAN
- Python 3.x インストール済み（`python` コマンドが通ること）
- Google Chrome インストール済み

---

### Step 1: `.env` を作成する（先生PC）

プロジェクトフォルダで `.env.example` をコピーして `.env` を作成します。

```powershell
Copy-Item .env.example .env
```

`.env` を開き、`TRIGGER_TOKEN` に任意の文字列を設定します。

```
TRIGGER_TOKEN=your_secret_token_here
```

> **注意:** このトークンは生徒PCにも配布されます。推測されにくい文字列にしてください。  
> 認証不要の場合は `TRIGGER_TOKEN=` （空欄）にすることもできます。

---

### Step 2: 先生PCをセットアップする

PowerShell を**管理者権限**で開き、以下を実行します。

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\setup_teacher.ps1
```

セットアップ内容:
- プロジェクトフォルダ内に `lessons\` フォルダを作成
- `lessons` フォルダをネットワーク共有（Everyone 読み取り）

完了後、以下を行います。

1. `lessons\` に各生徒の `.mkcd` ファイルを配置
2. `students.json` を編集（後述）
3. `mkcd_map.json` を編集（後述）

---

### Step 3: 生徒PCをセットアップする（各台）

このプロジェクトフォルダを生徒PCにコピーします（USBメモリ等）。

PowerShell を**管理者権限**で開き、以下を実行します。

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\setup_student.ps1
```

画面の指示に従い **PC番号（01〜09）** を入力します。

セットアップ内容:
- ポート 8080 のファイアウォールルールを追加（全プロファイル対象）
- `selenium` をインストール
- `trigger_server.py` をログオン時自動起動として登録（スタートアップフォルダ）
- `trigger_server.py` を即時起動し、動作確認

完了後、**再起動**します（コンピュータ名変更の反映に必要）。

> 再起動後、ログオン時に `trigger_server.py` が自動的にバックグラウンドで起動します。

---

### Step 4: `students.json` を編集する

プロジェクトフォルダ内の `students.json` を編集します。

```json
{
  "site_url": "https://your-site.com/login",
  "mkcd_share": "\\\\TEACHER-PC\\lessons\\",
  "last_assignment": {},
  "students": [
    {
      "id": "s001",
      "name": "田中太郎",
      "weekday": 1,
      "class": 1,
      "login_id": "tanaka@example.com",
      "login_pw": "pass123",
      "next_mkcd": "tanaka_lesson2.mkcd"
    }
  ]
}
```

| キー | 説明 |
|---|---|
| `site_url` | ログインページのURL |
| `mkcd_share` | 先生PCの共有フォルダパス（`\\コンピュータ名\lessons\`） |
| `weekday` | 曜日（0=月〜6=日）。GUIでのグループ表示に使用 |
| `class` | クラス番号。GUIでのグループ表示に使用 |
| `next_mkcd` | 次回起動するワールドのデフォルトファイル名 |

---

### Step 5: `mkcd_map.json` を編集する

GUIのプルダウンに表示するワールド名と実際のファイル名の対応表です。

```json
[
  {"display": "レッスン1-1", "file": "lesson1-1.mkcd"},
  {"display": "レッスン1-2", "file": "lesson1-2.mkcd"}
]
```

---

### Step 6: `agent.py` のセレクタを設定する

`agent.py` 内の `TODO` コメント箇所を、実際のログインサイトのHTML構造に合わせて変更します。

```python
# ログインIDフィールド
id_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='uid']")))
# パスワードフィールド
pw_field = driver.find_element(By.CSS_SELECTOR, "input[name='pwd']")
# ログインボタン
submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
```

---

## 使い方

### 先生PC でアプリを起動

```powershell
python teacher_app.py
```

### タブ1「授業開始」

1. 起動時にネットワーク上の `PC-01`〜`PC-09` を自動検出
2. 各PC行のドロップダウンで生徒とステージを割り当て
3. 「全PC起動」ボタンで全台を並列起動
4. 「更新」ボタンでPCを再スキャン
5. 前回の割り当ては次回起動時に自動復元

### タブ2「次回ワールド設定」

1. 各生徒の次回ワールドをプルダウンで選択
2. 「保存」ボタンで `students.json` に書き込み、タブ1にも即時反映

---

## ディレクトリ構成

すべてプロジェクトフォルダ内で完結します。アンインストールはフォルダごと削除するだけです。

| 場所 | 説明 |
|---|---|
| `プロジェクトフォルダ\` | 作業ディレクトリ（先生・生徒共通） |
| `プロジェクトフォルダ\lessons\` | `.mkcd` ファイル置き場（先生PCのみ・共有） |
| `プロジェクトフォルダ\students.json` | 設定ファイル（先生PCのみ） |
| `プロジェクトフォルダ\agent.py` | ブラウザ操作スクリプト（生徒PCのみ） |
| `プロジェクトフォルダ\trigger_server.py` | 常駐サーバー（生徒PCのみ） |
| `プロジェクトフォルダ\.env` | トークン（先生・生徒共通） |
| `プロジェクトフォルダ\trigger_server.log` | サーバーログ（生徒PC） |

---

## トラブルシューティング

### 「全PC起動」でタイムアウトする

生徒PCのポート 8080 がブロックされているか、`trigger_server.py` が動いていない可能性があります。

**生徒PCのPowerShell（管理者）で確認:**

```powershell
# サーバーが動いているか確認（:8080 が表示されればOK）
netstat -an | findstr ":8080"
```

表示されない場合は手動で起動します（プロジェクトフォルダで実行）。

```powershell
$pythonwExe = Join-Path (Split-Path (Get-Command python).Source) "pythonw.exe"
Start-Process -FilePath $pythonwExe -ArgumentList "`".\trigger_server.py`"" -WindowStyle Hidden
Start-Sleep 2
netstat -an | findstr ":8080"
```

---

### 403 エラーが出る（トークン不一致）

先生PCと生徒PCの `TRIGGER_TOKEN` が一致していません。

**確認方法:**

```powershell
# 先生PC・生徒PC ともにプロジェクトフォルダで
cat .\.env
```

両方の値が同じになるよう揃えます。同一LAN内で認証不要にする場合は両方 `TRIGGER_TOKEN=` （空欄）にしてください。

生徒PCの `.env` を更新したら `trigger_server.py` を再起動します。

```powershell
Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force
$pythonwExe = Join-Path (Split-Path (Get-Command python).Source) "pythonw.exe"
Start-Process -FilePath $pythonwExe -ArgumentList "`".\trigger_server.py`"" -WindowStyle Hidden
```

---

### PC が検出されない（0台と表示される）

- 生徒PCが起動・ログオン済みであること
- 先生PCと生徒PCが同一LANに接続されていること
- コンピュータ名が `PC-01`〜`PC-09` 形式になっていること（`setup_student.ps1` で設定）
- 再起動してコンピュータ名の変更が反映されていること
- タブ1の「更新」ボタンで再スキャンを試す

---

### trigger_server のログを確認する

```powershell
# 生徒PC（プロジェクトフォルダで）
cat .\trigger_server.log
```

---

## 補足
@memorandum
