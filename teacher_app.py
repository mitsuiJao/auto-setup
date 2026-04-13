"""
teacher_app.py - 先生PC用GUIアプリ
"""

import json
import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox

DATA_FILE = os.path.join(os.path.dirname(__file__), "students.json")
FONT = ("Yu Gothic", 11)
FONT_BOLD = ("Yu Gothic", 11, "bold")
PC_NAMES = [f"PC-{i:02d}" for i in range(1, 6)]
AGENT_PATH = r"C:\school\agent.py"


def load_data():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
    def _build_tab1(self):
        frame = self.tab1
        ttk.Label(frame, text="PC割り当て", font=FONT_BOLD).grid(
            row=0, column=0, columnspan=4, pady=(8, 4), sticky="w", padx=10)

        headers = ["PC名", "生徒", "次回ワールド"]
        for col, h in enumerate(headers):
            ttk.Label(frame, text=h, font=FONT_BOLD).grid(
                row=1, column=col, padx=8, pady=2, sticky="w")

        self.pc_student_vars = {}   # pc_name -> StringVar
        self.pc_world_labels = {}   # pc_name -> Label

        student_names = ["（未割当）"] + [s["name"] for s in self.data["students"]]

        for i, pc in enumerate(PC_NAMES):
            row = i + 2
            ttk.Label(frame, text=pc, font=FONT).grid(
                row=row, column=0, padx=8, pady=3, sticky="w")

            var = tk.StringVar(value="（未割当）")
            self.pc_student_vars[pc] = var
            cb = ttk.Combobox(frame, textvariable=var, values=student_names,
                              state="readonly", font=FONT, width=14)
            cb.grid(row=row, column=1, padx=8, pady=3, sticky="w")
            cb.bind("<<ComboboxSelected>>", lambda e, p=pc: self._on_student_selected(p))

            lbl = ttk.Label(frame, text="", font=FONT, foreground="#555")
            lbl.grid(row=row, column=2, padx=8, pady=3, sticky="w")
            self.pc_world_labels[pc] = lbl

        btn_row = len(PC_NAMES) + 2
        self.launch_btn = ttk.Button(
            frame, text="全PC起動", command=self._launch_all)
        self.launch_btn.grid(row=btn_row, column=0, columnspan=2,
                             padx=10, pady=10, sticky="w")

        self.status_label = ttk.Label(frame, text="", font=FONT)
        self.status_label.grid(row=btn_row, column=2, columnspan=2,
                               padx=8, pady=10, sticky="w")

    def _on_student_selected(self, pc_name):
        name = self.pc_student_vars[pc_name].get()
        lbl = self.pc_world_labels[pc_name]
        if name == "（未割当）":
            lbl.config(text="")
            return
        student = self._find_student_by_name(name)
        if student:
            lbl.config(text=student.get("next_mkcd", ""))

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
                self._on_student_selected(pc)

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
        self.status_label.config(text=f"起動中… (0/{len(assignments)})")

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
            else:
                msg = f"全{len(assignments)}台 起動成功"
            self.status_label.config(text=msg)
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

        headers = ["生徒名", "現在のワールド", "次回ワールド（編集可）"]
        for col, h in enumerate(headers):
            ttk.Label(frame, text=h, font=FONT_BOLD).grid(
                row=1, column=col, padx=8, pady=2, sticky="w")

        self.world_entries = {}  # student_id -> Entry

        for i, student in enumerate(self.data["students"]):
            row = i + 2
            ttk.Label(frame, text=student["name"], font=FONT).grid(
                row=row, column=0, padx=8, pady=3, sticky="w")
            ttk.Label(frame, text=student.get("next_mkcd", ""), font=FONT,
                      foreground="#555").grid(
                row=row, column=1, padx=8, pady=3, sticky="w")

            var = tk.StringVar(value=student.get("next_mkcd", ""))
            entry = ttk.Entry(frame, textvariable=var, font=FONT, width=24)
            entry.grid(row=row, column=2, padx=8, pady=3, sticky="w")
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
                student["next_mkcd"] = self.world_entries[sid].get()

        save_data(self.data)
        self.tab2_status.config(text="保存しました")

        # タブ1の表示を即時反映
        for pc, var in self.pc_student_vars.items():
            self._on_student_selected(pc)

        # タブ2の「現在のワールド」列を再描画
        for widget in self.tab2.winfo_children():
            widget.destroy()
        self._build_tab2()


if __name__ == "__main__":
    app = TeacherApp()
    app.mainloop()
