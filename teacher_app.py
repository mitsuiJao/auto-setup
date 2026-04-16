"""
teacher_app.py - 先生PC用GUIアプリ
"""

import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import ttk, messagebox

# PyInstaller --onefile ビルド時は __file__ が一時展開フォルダを指すため
# sys.executable（EXEファイル自身）のディレクトリを使う
_HERE = (os.path.dirname(sys.executable)
         if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    filename=os.path.join(_HERE, "teacher_app.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)
log = logging.getLogger(__name__)

DATA_FILE = os.path.join(_HERE, "students.json")
MKCD_MAP_FILE = os.path.join(_HERE, "mkcd_map.json")
FONT = ("Yu Gothic", 11)
FONT_BOLD = ("Yu Gothic", 11, "bold")
WEEKDAY_NAMES = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
DETECTION_TIMEOUT = 60  # PC検出のタイムアウト（秒）
TRIGGER_PORT = 8080      # 生徒PCのトリガーサーバーポート
STAGE_UNSET = "（未選択）"


def _load_env():
    """スクリプトと同ディレクトリの .env を読み込む"""
    env_path = os.path.join(_HERE, ".env")
    env = {}
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env


_env = _load_env()
TRIGGER_TOKEN = _env.get("TRIGGER_TOKEN", "")  # 生徒PCのトリガーサーバー認証トークン


def load_data():
    # H-2: ファイル欠損・破損時に分かりやすいエラーを表示して終了
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        messagebox.showerror("起動エラー",
                             f"設定ファイルが見つかりません。\n{DATA_FILE}\n\n"
                             "students.json.example を参考に作成してください。")
        sys.exit(1)
    except json.JSONDecodeError as e:
        messagebox.showerror("起動エラー",
                             f"students.json の読み込みに失敗しました。\n{e}")
        sys.exit(1)
    # 実行中のPCのホスト名を自動取得してmkcd_shareを上書き
    hostname = socket.gethostname()
    data["mkcd_share"] = f"\\\\{hostname}\\lessons\\"
    return data


def save_data(data):
    # H-3: アトミック書き込み — 書き込み中のクラッシュでファイルが壊れないよう
    # 一時ファイルに書いてから os.replace() で原子的に置き換える
    tmp_fd, tmp_path = tempfile.mkstemp(dir=_HERE, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, DATA_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_mkcd_map():
    """mkcd_map.json を読み込み、変換辞書を返す。
    Returns:
        displays     : list[str]   プルダウン表示用ラベル一覧
        file_to_disp : dict        file名 -> display名
        disp_to_file : dict        display名 -> file名
    """
    with open(MKCD_MAP_FILE, encoding="utf-8") as f:
        entries = json.load(f)
    displays = [e["display"] for e in entries]
    file_to_disp = {e["file"]: e["display"] for e in entries}
    disp_to_file = {e["display"]: e["file"] for e in entries}
    return displays, file_to_disp, disp_to_file


def detect_pc_names(max_pc: int = 10):
    """PC-01〜PC-{max_pc} に直接ホスト名でpingして応答があったPCを返す"""
    log.info("PC検出開始: PC-01〜PC-%02d", max_pc)

    ps_script = f"""
$ErrorActionPreference = "SilentlyContinue"

$jobs = 1..{max_pc} | ForEach-Object {{
    $name = "PC-{{0:D2}}" -f $_
    $p = [System.Net.NetworkInformation.Ping]::new()
    [PSCustomObject]@{{ Name = $name; Task = $p.SendPingAsync($name, 1000); Pinger = $p }}
}}
[System.Threading.Tasks.Task]::WaitAll($jobs.Task)

$jobs | ForEach-Object {{
    if ($_.Task.Result.Status -eq 'Success') {{
        Write-Host "[OK] $($_.Name)"
    }}
    $_.Pinger.Dispose()
}}
"""

    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, text=True, timeout=DETECTION_TIMEOUT
        )

        pc_list = sorted([
            line.strip().replace("[OK] ", "")
            for line in result.stdout.strip().split('\n')
            if line.strip().startswith("[OK]")
        ])

        if pc_list:
            log.info("PC検出完了: %d 台を検出: %s", len(pc_list), ', '.join(pc_list))
            return pc_list
        else:
            log.info("PC検出: 応答するPCが見つかりません")

    except subprocess.TimeoutExpired:
        log.warning("PC検出タイムアウト")
    except Exception as e:
        log.error("PC検出エラー: %s", e)

    # フォールバック: デフォルトのPC リスト
    fallback_pcs = [f"PC-{i:02d}" for i in range(1, 10)]
    log.info("デフォルト PC-01〜PC-09 を使用")
    return fallback_pcs


def launch_pc(pc_name, student, mkcd_file, site_url, mkcd_share):
    """HTTP POST で生徒PCのトリガーサーバーに agent.py を起動させる"""
    mkcd_path = mkcd_share.rstrip("\\") + "\\" + mkcd_file
    payload = json.dumps({
        "token":    TRIGGER_TOKEN,
        "login_id": student["login_id"],
        "login_pw": student["login_pw"],
        "mkcd_path": mkcd_path,
        "site_url":  site_url,
    }).encode("utf-8")

    url = f"http://{pc_name}:{TRIGGER_PORT}/start"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            if body.get("status") == "ok":
                log.info("%s 起動成功", pc_name)
                return True
            log.warning("%s サーバー応答エラー: %s", pc_name, body)
            return False
    except urllib.error.HTTPError as e:
        log.error("%s HTTPエラー %s: %s", pc_name, e.code, e.read().decode())
    except urllib.error.URLError as e:
        log.error("%s 接続失敗: %s", pc_name, e.reason)
    except Exception as e:
        log.error("%s エラー: %s", pc_name, e)
    return False


class TeacherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("塾PC管理ツール")
        self.resizable(False, False)
        self.configure(bg="#f0f0f0")

        self.data = load_data()
        self.mkcd_displays, self.file_to_disp, self.disp_to_file = load_mkcd_map()
        self.pc_names = detect_pc_names()  # ネットワークからPC検出
        self._separators: set[str] = set()
        self.pc_student_vars: dict[str, tk.StringVar] = {}
        self.pc_stage_vars: dict[str, tk.StringVar] = {}
        self.pc_stage_cbs: dict[str, ttk.Combobox] = {}
        self._build_ui()
        self._restore_last_assignment()

    # ------------------------------------------------------------------ UI構築
    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab1 = ttk.Frame(nb)
        self.tab2 = ttk.Frame(nb)
        nb.add(self.tab1, text="授業開始")
        nb.add(self.tab2, text="次回ワールド設定")

        self._build_tab1()
        self._build_tab2()

    # ---------------------------------------------------------- タブ1: 授業開始
    def _build_grouped_student_list(self) -> tuple[list[str], set[str]]:
        """weekday → class の順でグループ化した選択肢リストを返す。
        Returns:
            items      : コンボボックスに渡す文字列リスト
            separators : 選択不可にするセパレーター文字列の集合
        """
        students = sorted(
            self.data["students"],
            key=lambda s: (s.get("weekday", 99), s.get("class", 99))
        )
        items: list[str] = ["（未割当）"]
        separators: set[str] = set()
        prev_key = None
        for s in students:
            key = (s.get("weekday", 99), s.get("class", 99))
            if key != prev_key:
                wd = WEEKDAY_NAMES.get(key[0], f"{key[0]}曜")
                sep = f"── {wd}曜 クラス{key[1]} ──"
                items.append(sep)
                separators.add(sep)
                prev_key = key
            items.append(s["name"])
        return items, separators

    def _build_tab1(self):
        frame = self.tab1
        ttk.Label(frame, text="PC割り当て", font=FONT_BOLD).grid(
            row=0, column=0, columnspan=4, pady=(8, 4), sticky="w", padx=10)

        headers = ["PC名", "生徒", "ステージ"]
        for col, h in enumerate(headers):
            ttk.Label(frame, text=h, font=FONT_BOLD).grid(
                row=1, column=col, padx=8, pady=2, sticky="w")

        self.pc_student_vars = {}
        self.pc_stage_vars = {}
        self.pc_stage_cbs = {}

        student_items, self._separators = self._build_grouped_student_list()

        for i, pc in enumerate(self.pc_names):
            row = i + 2

            ttk.Label(frame, text=pc, font=FONT).grid(
                row=row, column=0, padx=8, pady=3, sticky="w")

            # 生徒コンボボックス
            student_var = tk.StringVar(value="（未割当）")
            self.pc_student_vars[pc] = student_var
            student_cb = ttk.Combobox(frame, textvariable=student_var,
                                      values=student_items,
                                      state="readonly", font=FONT, width=18)
            student_cb.grid(row=row, column=1, padx=8, pady=3, sticky="w")

            # ステージコンボボックス（初期は未割当なので未選択を含む）
            stage_var = tk.StringVar(value=STAGE_UNSET)
            self.pc_stage_vars[pc] = stage_var
            stage_cb = ttk.Combobox(frame, textvariable=stage_var,
                                    values=[STAGE_UNSET] + self.mkcd_displays,
                                    state="readonly", font=FONT, width=18)
            stage_cb.grid(row=row, column=2, padx=8, pady=3, sticky="w")
            self.pc_stage_cbs[pc] = stage_cb

            student_cb.bind("<<ComboboxSelected>>",
                            self._make_student_changed(pc, student_var, stage_var, stage_cb))

        btn_row = len(self.pc_names) + 2

        self.refresh_btn = ttk.Button(frame, text="更新", command=self._refresh_pcs)
        self.refresh_btn.grid(row=btn_row, column=0, padx=10, pady=10, sticky="w")

        self.launch_btn = ttk.Button(frame, text="全PC起動", command=self._launch_all)
        self.launch_btn.grid(row=btn_row, column=1, padx=(0, 8), pady=10, sticky="w")

        self.status_label = ttk.Label(frame, text="", font=FONT)
        self.status_label.grid(row=btn_row, column=2, padx=8, pady=10, sticky="w")

    def _make_student_changed(self, pc, student_var, stage_var, stage_cb):
        """生徒コンボボックス変更時のコールバックを返す"""
        def on_changed(event):
            name = student_var.get()

            # セパレーターが選ばれたら未割当に戻す
            if name in self._separators:
                student_var.set("（未割当）")
                name = "（未割当）"

            if name == "（未割当）":
                # 未割当: ステージに未選択を含む全リストを設定
                stage_cb.config(values=[STAGE_UNSET] + self.mkcd_displays)
                stage_var.set(STAGE_UNSET)
            else:
                # 生徒確定: 未選択を選択肢から除外し、その生徒の next_mkcd をデフォルトに
                stage_cb.config(values=self.mkcd_displays)
                student = self._find_student_by_name(name)
                default_disp = ""
                if student:
                    default_disp = self.file_to_disp.get(student.get("next_mkcd", ""), "")
                if default_disp in self.mkcd_displays:
                    stage_var.set(default_disp)
                elif self.mkcd_displays:
                    stage_var.set(self.mkcd_displays[0])

        return on_changed

    def _find_student_by_name(self, name):
        for s in self.data["students"]:
            if s["name"] == name:
                return s
        return None

    def _restore_last_assignment(self):
        last = self.data.get("last_assignment", {})
        last_stage = self.data.get("last_stage", {})

        for pc, student_id in last.items():
            if pc not in self.pc_student_vars:
                continue
            student = next((s for s in self.data["students"] if s["id"] == student_id), None)
            if not student:
                continue

            # 生徒をセット
            self.pc_student_vars[pc].set(student["name"])

            # ステージをセット: last_stage があればそれを優先、なければ next_mkcd
            stage_file = last_stage.get(pc, student.get("next_mkcd", ""))
            stage_disp = self.file_to_disp.get(stage_file, "")

            if pc in self.pc_stage_cbs:
                # 生徒が確定しているので未選択を除外
                self.pc_stage_cbs[pc].config(values=self.mkcd_displays)
                if stage_disp in self.mkcd_displays:
                    self.pc_stage_vars[pc].set(stage_disp)
                elif self.mkcd_displays:
                    self.pc_stage_vars[pc].set(self.mkcd_displays[0])

    def _launch_all(self):
        # 割り当て: {pc: (student, mkcd_file)}
        assignments: dict[str, tuple[dict, str]] = {}
        skipped_no_student = []

        for pc, student_var in self.pc_student_vars.items():
            name = student_var.get()
            stage_disp = self.pc_stage_vars[pc].get()

            if name == "（未割当）":
                if stage_disp != STAGE_UNSET:
                    # 生徒未割当でステージのみ選択 → スキップ
                    skipped_no_student.append(pc)
                continue

            student = self._find_student_by_name(name)
            if not student:
                continue

            # 生徒確定時にステージが未選択になることは通常ないが念のため
            if stage_disp == STAGE_UNSET:
                continue

            mkcd_file = self.disp_to_file.get(stage_disp, stage_disp)
            assignments[pc] = (student, mkcd_file)

        if skipped_no_student:
            log.warning("生徒未割当のためスキップ: %s", ', '.join(skipped_no_student))

        if not assignments:
            messagebox.showwarning("警告", "割り当て済みのPCがありません。", parent=self)
            return

        self.launch_btn.config(state="disabled")
        self.refresh_btn.config(state="disabled")
        self.status_label.config(text=f"起動中… (0/{len(assignments)})", foreground="")

        def worker():
            results = {}
            lock = threading.Lock()
            threads = []

            def run(pc, student, mkcd_file):
                ok = launch_pc(
                    pc, student, mkcd_file,
                    self.data["site_url"],
                    self.data["mkcd_share"],
                )
                with lock:
                    results[pc] = ok
                    done = len(results)
                    # H-1: GUI 更新はメインスレッドで行う
                    self.after(0, lambda d=done: self.status_label.config(
                        text=f"起動中… ({d}/{len(assignments)})"))

            for pc, (student, mkcd_file) in assignments.items():
                t = threading.Thread(target=run, args=(pc, student, mkcd_file), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # H-1 & H-4: GUI 更新と save_data をまとめてメインスレッドへ
            def finalize():
                errors = [pc for pc, ok in results.items() if not ok]
                if errors:
                    self.status_label.config(
                        text=f"完了（エラー {len(errors)} 台）", foreground="red")
                else:
                    self.status_label.config(
                        text=f"全{len(assignments)}台 起動成功", foreground="")
                self.launch_btn.config(state="normal")
                self.refresh_btn.config(state="normal")

                # last_assignment / last_stage を保存（メインスレッドから呼ぶ）
                self.data["last_assignment"] = {pc: s["id"] for pc, (s, _) in assignments.items()}
                self.data["last_stage"] = {pc: f for pc, (_, f) in assignments.items()}
                save_data(self.data)
                log.info("割り当て保存完了: %s", self.data["last_assignment"])

            self.after(0, finalize)

        threading.Thread(target=worker, daemon=True).start()

    # ---------------------------------------------------------- PC再スキャン
    def _refresh_pcs(self):
        """PC一覧を再スキャンしてタブ1を再描画する"""
        self.refresh_btn.config(state="disabled")
        self.launch_btn.config(state="disabled")
        self.status_label.config(text="PCをスキャン中…", foreground="")

        def do_refresh():
            self.pc_names = detect_pc_names()
            self.after(0, self._rebuild_tab1)

        threading.Thread(target=do_refresh, daemon=True).start()

    def _rebuild_tab1(self):
        for widget in self.tab1.winfo_children():
            widget.destroy()
        self._build_tab1()
        self._restore_last_assignment()

    # ------------------------------------------------- タブ2: 次回ワールド設定
    def _build_tab2(self):
        frame = self.tab2
        ttk.Label(frame, text="次回ワールド設定", font=FONT_BOLD).grid(
            row=0, column=0, columnspan=3, pady=(8, 4), sticky="w", padx=10)

        headers = ["生徒名", "現在のワールド", "次回ワールド（選択）"]
        for col, h in enumerate(headers):
            ttk.Label(frame, text=h, font=FONT_BOLD).grid(
                row=1, column=col, padx=8, pady=2, sticky="w")

        self.world_entries = {}  # student_id -> StringVar (display名を保持)

        for i, student in enumerate(self.data["students"]):
            row = i + 2
            ttk.Label(frame, text=student["name"], font=FONT).grid(
                row=row, column=0, padx=8, pady=3, sticky="w")

            # 現在のワールドを display 名で表示
            current_file = student.get("next_mkcd", "")
            current_disp = self.file_to_disp.get(current_file, current_file)
            ttk.Label(frame, text=current_disp, font=FONT,
                      foreground="#555").grid(
                row=row, column=1, padx=8, pady=3, sticky="w")

            # プルダウン（display 名一覧）
            var = tk.StringVar(value=current_disp)
            cb = ttk.Combobox(frame, textvariable=var,
                              values=self.mkcd_displays,
                              state="readonly", font=FONT, width=16)
            cb.grid(row=row, column=2, padx=8, pady=3, sticky="w")
            self.world_entries[student["id"]] = var

        save_row = len(self.data["students"]) + 2
        ttk.Button(frame, text="保存", command=self._save_worlds).grid(
            row=save_row, column=0, padx=10, pady=10, sticky="w")

        self.tab2_status = ttk.Label(frame, text="", font=FONT)
        self.tab2_status.grid(row=save_row, column=1, columnspan=2,
                              padx=8, pady=10, sticky="w")

    def _save_worlds(self):
        for student in self.data["students"]:
            sid = student["id"]
            if sid in self.world_entries:
                disp = self.world_entries[sid].get()
                # display名 -> file名 に変換して保存（マップにない場合はそのまま）
                student["next_mkcd"] = self.disp_to_file.get(disp, disp)

        save_data(self.data)
        self.tab2_status.config(text="保存しました")

        # タブ2の「現在のワールド」列を再描画
        for widget in self.tab2.winfo_children():
            widget.destroy()
        self._build_tab2()


if __name__ == "__main__":
    # シングルインスタンス確認（ローカルポートをロックとして使用）
    _lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock_sock.bind(("127.0.0.1", 47823))
    except OSError:
        _root = tk.Tk()
        _root.withdraw()
        messagebox.showerror("起動エラー", "アプリは既に起動しています。\n複数同時起動はできません。")
        sys.exit(0)

    app = TeacherApp()
    app.mainloop()
