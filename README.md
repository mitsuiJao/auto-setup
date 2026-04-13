# 塾PC管理ツール

## ファイル構成

| ファイル | 役割 |
|---|---|
| `teacher_app.py` | 先生PC用GUIアプリ |
| `agent.py` | 生徒PC全台に置くスクリプト |
| `trigger_server.py` | 生徒PC常駐サーバー（HTTP で agent.py を起動） |
| `students.json` | 生徒データ・設定 |
| `.env` | 認証トークン（gitignore済み） |
| `setup_student.ps1` | 生徒PC初期設定（1回だけ実行） |
| `setup_teacher.ps1` | 先生PC初期設定（1回だけ実行） |

## アーキテクチャ

```
先生PC
  teacher_app.py
      │  HTTP POST /start  (port 8080)
      ▼
生徒PC  trigger_server.py  ←── ログオン時に自動起動
                │
                └──▶ agent.py  (Selenium でブラウザ操作)
```

- **認証**: 共有トークン（`.env` の `TRIGGER_TOKEN`）で保護
- **外部依存なし**: urllib（標準ライブラリ）のみ使用。PsExec・WinRM 不要

## セットアップ手順

### 0. 事前準備（先生PC）

1. `.env.example` をコピーして `.env` を作成し、トークンを設定
   ```
   TRIGGER_TOKEN=任意のランダム文字列
   ```
   ※ このトークンは生徒PCに自動配布されます

### 1. 先生PC

1. `setup_teacher.ps1` を**管理者権限**で実行
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope Process
   .\setup_teacher.ps1
   ```
2. `%USERPROFILE%\AppData\Local\school\lessons\` に各生徒の `.mkcd` ファイルを配置
3. `students.json` を編集してログイン情報・サイトURLを設定
4. `mkcd_share` を `\\<先生PCのコンピュータ名>\lessons\` に設定

### 2. 生徒PC（各台）

1. このフォルダを生徒PCにコピー
2. `setup_student.ps1` を**管理者権限**で実行
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope Process
   .\setup_student.ps1
   ```
3. **PC番号を入力**（画面に従って `01`〜`09` を入力）
   - コンピュータ名が `PC-01`、`PC-02` などに自動変更されます
4. セットアップ完了後、**再起動**
   - 再起動後、`trigger_server.py` が自動的に起動します（ポート 8080）

### 3. agent.py のセレクタ設定

`agent.py` 内の `TODO` コメント箇所を、実際のログインサイトのHTML構造に合わせて変更してください。

```python
# ログインIDフィールド
id_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']")))
# パスワードフィールド
pw_field = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
# ログインボタン
submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
```

## 使い方

### 先生PC でアプリを起動

```powershell
python teacher_app.py
```

### タブ1「授業開始」

- **起動時に自動でネットワークからPC検出**
  - PC-01, PC-02, ... の形式の接続可能なPCを自動検出
  - 検出失敗時は PC-01～PC-09 をデフォルト表示
- 各PC行のドロップダウンで生徒を割り当て
- 「全PC起動」ボタンで全台を並列起動（HTTP POST 経由）
- 前回の割り当ては自動復元される

### タブ2「次回ワールド設定」

- 生徒ごとに次回の `.mkcd` ファイル名を選択
- 「保存」でタブ1の表示も即時反映

## students.json の編集例

```json
{
  "site_url": "https://your-site.com/login",
  "mkcd_share": "\\\\TEACHER-PC\\lessons\\",
  "last_assignment": {},
  "students": [
    {
      "id": "s001",
      "name": "田中太郎",
      "login_id": "tanaka@example.com",
      "login_pw": "pass123",
      "next_mkcd": "tanaka_lesson2.mkcd"
    }
  ]
}
```

**注意：** `mkcd_share` は、先生PCのコンピュータ名に合わせて設定してください。

## ディレクトリ構成

| 場所 | 説明 |
|------|------|
| `%USERPROFILE%\AppData\Local\school\` | 全体の作業ディレクトリ |
| `%USERPROFILE%\AppData\Local\school\lessons\` | .mkcdファイル置き場（共有） |
| `%USERPROFILE%\AppData\Local\school\students.json` | 設定ファイル |
| `%USERPROFILE%\AppData\Local\school\agent.py` | 生徒PC用スクリプト |
| `%USERPROFILE%\AppData\Local\school\trigger_server.py` | 生徒PC常駐サーバー |
| `%USERPROFILE%\AppData\Local\school\.env` | トークン（生徒PC用） |

## 前提条件

- 全台 Windows、同一LAN
- 生徒PC に Python + selenium インストール済み
- ChromeDriver が PATH に通っている、またはシステムに Chrome がインストール済み
- 生徒PCのポート 8080 が開放されている（setup スクリプトで設定）

## 補足
@memorandum
