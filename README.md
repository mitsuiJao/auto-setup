# 塾PC管理ツール

## ファイル構成

| ファイル | 役割 |
|---|---|
| `teacher_app.py` | 先生PC用GUIアプリ |
| `agent.py` | 生徒PC全台に置くスクリプト |
| `students.json` | 生徒データ・設定 |
| `setup_student.ps1` | 生徒PC初期設定（1回だけ実行） |
| `setup_teacher.ps1` | 先生PC初期設定（1回だけ実行） |

## セットアップ手順

### 1. 先生PC

1. `setup_teacher.ps1` を**管理者権限**で実行
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope Process
   .\setup_teacher.ps1
   ```
2. `C:\lessons\` に各生徒の `.mkcd` ファイルを配置
3. `students.json` を編集してログイン情報・サイトURLを設定
4. `mkcd_share` を `\\<先生PCのコンピュータ名>\lessons\` に設定

### 2. 生徒PC（各台）

1. このフォルダを生徒PCにコピー
2. `setup_student.ps1` を**管理者権限**で実行
   ```powershell
   Set-ExecutionPolicy RemoteSigned -Scope Process
   .\setup_student.ps1
   ```
   - `C:\school\agent.py` が配置されます
   - WinRM（PowerShell Remoting）が有効化されます

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

- 各PC行のドロップダウンで生徒を割り当て
- 「次回ワールド名」が自動表示される
- 「全PC起動」ボタンで全台を並列起動
- 前回の割り当ては自動復元される

### タブ2「次回ワールド設定」

- 生徒ごとに次回の `.mkcd` ファイル名を入力
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

## 前提条件

- 全台 Windows、同一LAN
- 先生PC・生徒PC ともに WinRM が有効（setup スクリプトで設定）
- 生徒PC に Python + selenium インストール済み
- ChromeDriver が PATH に通っている、またはシステムに Chrome がインストール済み
