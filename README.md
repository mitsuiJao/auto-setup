**バイトクビになりました。**

# 塾PC管理ツール

## 概要

先生PCのGUIアプリから、生徒PC全台に対してブラウザ自動操作（Selenium）を一括起動するツールです。

```
先生PC: 生徒PC起動アプリ.exe
    │  HTTP POST /start（ポート 8080）
    ▼
生徒PC: trigger_server.exe（常駐）
    │
    └──▶ agent.exe（Selenium でログイン・ワールド起動）
```

---

## ファイル構成

| ファイル | 説明 |
|---|---|
| `生徒PC起動アプリ.exe` | 先生PC用GUIアプリ |
| `agent.exe` | 生徒PCで動くブラウザ自動操作 |
| `trigger_server.exe` | 生徒PC常駐HTTPサーバー（port 8080） |
| `students.json` | 生徒データ・設定（**要作成**・`students.json.example` から作成） |
| `students.json.example` | `students.json` のテンプレート |
| `mkcd_map.json` | ワールド名の表示名↔ファイル名対応表 |
| `.env` | 認証トークン（**要作成**・`.env.example` から作成、先生PC・生徒PC共通） |
| `.env.example` | `.env` のテンプレート |
| `setup_teacher.ps1` | 先生PC初期設定（1回だけ実行） |
| `setup_student.ps1` | 生徒PC初期設定（1回だけ実行） |
| `build.ps1` | EXEビルドスクリプト（開発環境のみ） |

---

## ビルド方法（開発環境）

Python + PyInstaller がインストールされた開発環境で実行します。

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\build.ps1
```

出力:
- `dist\teacher\` → 先生PC用配布物（`生徒PC起動アプリ.exe` / `students.json.example` / `mkcd_map.json` 等）
- `dist\student\` → 生徒PC用配布物（`trigger_server.exe` / `agent.exe` 等）

---

## セットアップ手順

### 前提条件（全台共通）

- Windows 10 / 11、全台同一LAN
- Google Chrome インストール済み

---

### Step 1: `.env` を作成する（先生PC）

配布フォルダで `.env.example` をコピーして `.env` を作成します。

```powershell
Copy-Item .env.example .env
```

`.env` を開き、`TRIGGER_TOKEN` に任意の文字列を設定します。

```
TRIGGER_TOKEN=your_secret_token_here
```

> **注意:** このトークンは生徒PCにも配布されます。推測されにくい文字列にしてください。  
> 認証不要の場合は `TRIGGER_TOKEN=` （空欄）にすることもできます。

作成した `.env` は、後の手順で生徒PC用配布フォルダにもコピーして配布します。

---

### Step 2: 先生PCをセットアップする

PowerShell を**管理者権限**で開き、以下を実行します。

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\setup_teacher.ps1
```

セットアップ内容:
- 配布フォルダ内に `lessons\` フォルダを作成
- `lessons` フォルダをネットワーク共有（認証済みユーザー 読み取り）

完了後、以下を行います。

1. `lessons\` に各生徒の `.mkcd` ファイルを配置
2. `students.json` を作成・編集（後述）
3. `mkcd_map.json` を編集（後述）

---

### Step 3: 生徒PCをセットアップする（各台）

**GitHub Releases からの配布（推奨）:**

1. GitHub Releases から `student-app.zip` をダウンロードして展開
2. Step 1 で作成した `.env` を展開したフォルダにコピー
3. USBメモリ等で生徒PCへ転送

**開発環境からの直接配布:**

1. `dist\student\` フォルダをコピー
2. Step 1 で作成した `.env` を `dist\student\` にコピー
3. USBメモリ等で生徒PCへ転送

生徒PCで PowerShell を**管理者権限**で開き、以下を実行します。

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\setup_student.ps1
```

画面の指示に従い **PC番号（01〜09）** を入力します。

セットアップ内容:
- ポート 8080 のファイアウォールルールを追加（全プロファイル対象）
- `trigger_server.exe` をログオン時自動起動として登録（スタートアップフォルダ）
- `trigger_server.exe` を即時起動し、動作確認

完了後、**再起動**します（コンピュータ名変更の反映に必要）。

> 再起動後、ログオン時に `trigger_server.exe` が自動的にバックグラウンドで起動します。

---

### Step 4: `students.json` を作成・編集する

`students.json.example` をコピーして `students.json` を作成し、編集します。

```powershell
Copy-Item students.json.example students.json
```

```json
{
  "site_url": "https://your-site.com/login",
  "mkcd_share": "",
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
| `mkcd_share` | 設定不要（アプリ起動時に先生PCのホスト名を自動取得） |
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

## 使い方

### 先生PC でアプリを起動

`生徒PC起動アプリ.exe` をダブルクリックして起動します。

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

すべて配布フォルダ内で完結します。アンインストールはフォルダごと削除するだけです。

| 場所 | 説明 |
|---|---|
| `配布フォルダ\` | 作業ディレクトリ |
| `配布フォルダ\lessons\` | `.mkcd` ファイル置き場（先生PCのみ・共有） |
| `配布フォルダ\students.json` | 生徒データ設定（先生PCのみ・要作成） |
| `配布フォルダ\students.json.example` | `students.json` のテンプレート（先生PCのみ） |
| `配布フォルダ\生徒PC起動アプリ.exe` | GUIアプリ（先生PCのみ） |
| `配布フォルダ\agent.exe` | ブラウザ操作（生徒PCのみ） |
| `配布フォルダ\trigger_server.exe` | 常駐サーバー（生徒PCのみ） |
| `配布フォルダ\.env` | トークン（先生・生徒共通・要作成） |
| `配布フォルダ\.env.example` | `.env` のテンプレート |
| `配布フォルダ\trigger_server.log` | サーバーログ（生徒PC） |

---

## トラブルシューティング

### 「全PC起動」でタイムアウトする

生徒PCのポート 8080 がブロックされているか、`trigger_server.exe` が動いていない可能性があります。

**生徒PCのPowerShell（管理者）で確認:**

```powershell
netstat -an | findstr ":8080"
```

表示されない場合は手動で起動します。

```powershell
Start-Process ".\trigger_server.exe" -WindowStyle Hidden
Start-Sleep 2
netstat -an | findstr ":8080"
```

---

### 403 エラーが出る（トークン不一致）

先生PCと生徒PCの `TRIGGER_TOKEN` が一致していません。

```powershell
# 先生PC・生徒PC ともに配布フォルダで
cat .\.env
```

生徒PCの `.env` を更新したら `trigger_server.exe` を再起動します。

```powershell
Get-Process trigger_server -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process ".\trigger_server.exe" -WindowStyle Hidden
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
cat .\trigger_server.log
```

---

## 補足

### ビルド成果物について

- **`dist/` フォルダは Git で管理していません** （`.gitignore` に含まれる）
- **修正方法：** Python コード修正 → `build.ps1` 実行 → `dist/` に新しい exe が生成される
- **別PCでの実行可否：** ビルド成果物（exe）は別PCでも実行可能です
  - **前提条件：** Chrome がインストール済み
  - **配布方法：** `dist\teacher\` と `dist\student\` フォルダの内容をそのまま配布

### 開発環境での管理

- **main**: 本番向け安定版
- **develop**: 開発・統合ブランチ（機能追加・修正時はここから作業）
- 修正後は develop → main へのマージを推奨
