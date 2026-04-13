"""
teacher_app.py - 先生PC用GUIアプリ
"""

import json
import os
import socket
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

SCHOOL_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", "school")
DATA_FILE = os.path.join(SCHOOL_DIR, "students.json")
MKCD_MAP_FILE = os.path.join(os.path.dirname(__file__), "mkcd_map.json")
FONT = ("Yu Gothic", 11)
FONT_BOLD = ("Yu Gothic", 11, "bold")
PC_NAMES = [f"PC-{i:02d}" for i in range(1, 6)]
AGENT_PATH = os.path.join(SCHOOL_DIR, "agent.py")
WEEKDAY_NAMES = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}


def load_data():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


def launch_pc(pc_name, student, site_url, mkcd_share):
    """PowerShell Remoting で生徒PCの agent.py を実行する"""
    mkcd_path = mkcd_share.rstrip("\\") + "\\" + student["next_mkcd"]
    cmd = (
        f'Invoke-Command -ComputerName {pc_name} -ScriptBlock {{'
        f' python "{AGENT_PATH}"'
        f' --login_id "{student["login_id"]}"'
        f' --login_pw "{student["login_pw"]}"'
        f' --mkcd_path "{mkcd_path}"'
        f' --site_url "{site_url}"'
        f' }}'
    )
    result = subprocess.run(
        ["powershell", "-Command", cmd],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[launch_pc] {pc_name} エラー: {result.stderr}")
        return False
    return True


class TeacherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("塾PC管理ツール")
        self.resizable(False, False)
        self.configure(bg="#f0f0f0")

        self.data = load_data()
        self.mkcd_displays, self.file_to_disp, self.disp_to_file = load_mkcd_map()
        self._separators: set[str] = set()
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

        headers = ["PC名", "生徒"]
        for col, h in enumerate(headers):
            ttk.Label(frame, text=h, font=FONT_BOLD).grid(
                row=1, column=col, padx=8, pady=2, sticky="w")

        self.pc_student_vars = {}   # pc_name -> StringVar

        student_items, self._separators = self._build_grouped_student_list()

        for i, pc in enumerate(PC_NAMES):
            row = i + 2
            ttk.Label(frame, text=pc, font=FONT).grid(
                row=row, column=0, padx=8, pady=3, sticky="w")

            var = tk.StringVar(value="（未割当）")
            self.pc_student_vars[pc] = var
            cb = ttk.Combobox(frame, textvariable=var, values=student_items,
                              state="readonly", font=FONT, width=18)
            cb.grid(row=row, column=1, padx=8, pady=3, sticky="w")
            cb.bind("<<ComboboxSelected>>", self._make_sep_guard(var))

        btn_row = len(PC_NAMES) + 2
        self.launch_btn = ttk.Button(
            frame, text="全PC起動", command=self._launch_all)
        self.launch_btn.grid(row=btn_row, column=0, columnspan=2,
                             padx=10, pady=10, sticky="w")

        self.status_label = ttk.Label(frame, text="", font=FONT)
        self.status_label.grid(row=btn_row, column=2, columnspan=2,
                               padx=8, pady=10, sticky="w")

    def _make_sep_guard(self, var: tk.StringVar):
        """セパレーターが選択されたら「（未割当）」に戻すコールバックを返す"""
        def guard(event):
            if var.get() in self._separators:
                var.set("（未割当）")
        return guard

    def _find_student_by_name(self, name):
        for s in self.data["students"]:
            if s["name"] == name:
                return s
        return None

    def _restore_last_assignment(self):
        last = self.data.get("last_assignment", {})
        for pc, student_id in last.items():
            if pc not in self.pc_student_vars:
                continue
            student = next((s for s in self.data["students"] if s["id"] == student_id), None)
            if student:
                self.pc_student_vars[pc].set(student["name"])

    def _launch_all(self):
        assignments = {}
        for pc, var in self.pc_student_vars.items():
            name = var.get()
            if name != "（未割当）":
                student = self._find_student_by_name(name)
                if student:
                    assignments[pc] = student

        if not assignments:
            messagebox.showwarning("警告", "割り当て済みのPCがありません。", parent=self)
            return

        self.launch_btn.config(state="disabled")
        self.status_label.config(text=f"起動中… (0/{len(assignments)})", foreground="")

        def worker():
            results = {}
            lock = threading.Lock()
            threads = []

            def run(pc, student):
                ok = launch_pc(
                    pc, student,
                    self.data["site_url"],
                    self.data["mkcd_share"]
                )
                with lock:
                    results[pc] = ok
                    done = len(results)
                    self.status_label.config(
                        text=f"起動中… ({done}/{len(assignments)})")

            for pc, student in assignments.items():
                t = threading.Thread(target=run, args=(pc, student), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            errors = [pc for pc, ok in results.items() if not ok]
            if errors:
                msg = f"完了（エラー {len(errors)} 台）"
                self.status_label.config(text=msg, foreground="red")
            else:
                msg = f"全{len(assignments)}台 起動成功"
                self.status_label.config(text=msg, foreground="")
            self.launch_btn.config(state="normal")

            # last_assignment を保存
            last = {pc: s["id"] for pc, s in assignments.items()}
            self.data["last_assignment"] = last
            save_data(self.data)

        threading.Thread(target=worker, daemon=True).start()

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
