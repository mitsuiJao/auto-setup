"""
trigger_server.py - 生徒PC常駐トリガーサーバー
teacher_app.py からの HTTP POST を受けて agent.py を起動する
"""

import json
import logging
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8080
MAX_BODY = 4096  # H-6: リクエストボディの上限 (4KB)
_HERE = (os.path.dirname(sys.executable)
         if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.abspath(__file__)))
AGENT_PATH = (os.path.join(_HERE, "agent.exe")
              if getattr(sys, "frozen", False)
              else os.path.join(_HERE, "agent.py"))
LOG_FILE = os.path.join(_HERE, "trigger_server.log")

# pythonw.exe はコンソールがないのでファイルにログを書く
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)
log = logging.getLogger(__name__)


def _load_token():
    """自身と同ディレクトリの .env から TRIGGER_TOKEN を読む"""
    env_path = os.path.join(_HERE, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "TRIGGER_TOKEN":
                        return v.strip().strip('"').strip("'")
    return ""


TRIGGER_TOKEN = _load_token()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log.info("[%s] %s", self.client_address[0], format % args)

    def do_POST(self):
        if self.path != "/start":
            self._respond(404, {"error": "not found"})
            return

        # H-6: Content-Length を検証し過大なリクエストを拒否
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self._respond(400, {"error": "invalid content-length"})
            return
        if length > MAX_BODY:
            self._respond(400, {"error": "request too large"})
            return

        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except Exception:
            self._respond(400, {"error": "invalid json"})
            return

        # トークン認証
        if TRIGGER_TOKEN and payload.get("token") != TRIGGER_TOKEN:
            log.warning("認証失敗: token不一致")
            self._respond(403, {"error": "forbidden"})
            return

        login_id   = payload.get("login_id",   "")
        login_pw   = payload.get("login_pw",   "")
        mkcd_path  = payload.get("mkcd_path",  "")
        site_url   = payload.get("site_url",   "")
        stage_path = payload.get("stage_path", "")

        # H-5: 必須フィールドの存在チェック
        missing = [k for k, v in [("login_id", login_id), ("login_pw", login_pw),
                                   ("mkcd_path", mkcd_path), ("site_url", site_url)] if not v]
        if missing:
            log.warning("必須フィールドが欠けています: %s", missing)
            self._respond(400, {"error": f"missing fields: {missing}"})
            return

        # H-5: パストラバーサル対策
        if ".." in mkcd_path:
            log.warning("不正なパスを検出: %s", mkcd_path)
            self._respond(400, {"error": "invalid path"})
            return

        # EXE時は agent.exe を直接呼ぶ。スクリプト時は python interpreter 経由
        base_cmd = [AGENT_PATH] if getattr(sys, "frozen", False) else [sys.executable, AGENT_PATH]
        cmd = base_cmd + [
            "--login_id",  login_id,
            "--login_pw",  login_pw,
            "--mkcd_path", mkcd_path,
            "--site_url",  site_url,
        ]
        if stage_path:
            cmd += ["--stage_path", stage_path]

        # M-6: agent ファイルの存在確認（起動前に問題を早期検知）
        if not os.path.exists(AGENT_PATH):
            log.error("agent が見つかりません: %s", AGENT_PATH)
            self._respond(500, {"error": "agent not found"})
            return

        try:
            # CREATE_NEW_CONSOLE でユーザーセッションの新しいウィンドウとして起動
            proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            # M-6: Popen 直後に poll() でプロセスが即死していないか確認
            if proc.poll() is not None:
                log.error("agent がすぐに終了しました (exit_code=%d)", proc.returncode)
                self._respond(500, {"error": f"agent exited immediately (code={proc.returncode})"})
                return
            log.info("agent を起動しました: %s", AGENT_PATH)
            self._respond(200, {"status": "ok"})
        except Exception as e:
            log.error("起動エラー: %s", e)
            self._respond(500, {"error": str(e)})

    def _respond(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    log.info("ポート %d で待機開始", PORT)
    # M-7: ポート競合時に分かりやすいメッセージを出して安全に終了
    try:
        server = HTTPServer(("0.0.0.0", PORT), Handler)
    except OSError as e:
        log.critical("ポート %d が使用中です（別プロセスが起動済みの可能性）: %s", PORT, e)
        sys.exit(1)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("サーバーを停止しました")
    except Exception as e:
        log.critical("サーバー実行中エラー: %s", e)
        raise
