以下の仕様で、塾のPC管理ツールを実装してください。

## プロジェクト構成
teacher_app.py   # 先生PC用GUIアプリ
agent.py         # 生徒PC全台に置くスクリプト
students.json    # 生徒データ・設定
setup_student.ps1  # 生徒PC初期設定用（1回だけ実行）
setup_teacher.ps1  # 先生PC初期設定用（1回だけ実行）
README.md

## 環境
- 全台Windows
- 同一LAN内、台数は10未満
- Minecraft Education Edition（.mkcdファイルをダブルクリックで起動）
- .mkcdは先生PCの共有フォルダに生徒ごとに置く
- 生徒PCにはPythonとSeleniumをインストール済み前提

## students.json の構造
{
  "site_url": "https://example.com",
  "mkcd_share": "\\\\TEACHER-PC\\lessons\\",
  "last_assignment": {},
  "students": [
    {
      "id": "s001",
      "name": "田中太郎",
      "login_id": "tanaka@example.com",
      "login_pw": "pass123",
      "next_mkcd": "tanaka_lesson1.mkcd"
    }
  ]
}

## teacher_app.py の仕様
タブ1「授業開始」
- PC名の一覧（PC-01〜PC-05）を表示
- 各行に生徒をドロップダウンで割り当て（未割当も選択可）
- 割り当てると「次回ワールド名」が横に表示される
- 前回の割り当てをstudents.jsonのlast_assignmentから起動時に自動復元
- 「全PC起動」ボタンで割り当て済みの全PCを並列起動
- 起動成功後、今回の割り当てをlast_assignmentに保存
- ステータス表示あり

タブ2「次回ワールド設定」
- 全生徒の「現在のワールド」「次回ワールド（入力欄）」を一覧表示
- 「保存」でstudents.jsonを更新
- 保存後タブ1の表示も即時反映

## agent.py の仕様
- コマンドライン引数: --login_id, --login_pw, --mkcd_path, --site_url
- ChromeをSeleniumで起動してsite_urlにアクセス
- ログインフォームに入力してsubmit（セレクタはTODOコメントで明示）
- ログイン後にos.startfile()で.mkcdを開く

## launch_pc()の仕様
- PowerShell Remotingを使い先生PCから生徒PCのagent.pyを実行
- agent.pyのパスは %USERPROFILE%\AppData\Local\school\agent.py

## その他
- UIはtkinter（ttk使用）
- フォントはYu Gothic
- エラーはコンソールにprint、GUIにはエラー台数のみ表示
- students.jsonはUTF-8で読み書き