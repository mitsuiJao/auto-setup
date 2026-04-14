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
_HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_PATH = os.path.join(_HERE, "agent.py")
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

        length = int(self.headers.get("Content-Length", 0))
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

        login_id  = payload.get("login_id",  "")
        login_pw  = payload.get("login_pw",  "")
        mkcd_path = payload.get("mkcd_path", "")
        site_url  = payload.get("site_url",  "")

        cmd = [sys.executable, AGENT_PATH,
               "--login_id",  login_id,
               "--login_pw",  login_pw,
               "--mkcd_path", mkcd_path,
               "--site_url",  site_url]

        try:
            # CREATE_NEW_CONSOLE でユーザーセッションの新しいウィンドウとして起動
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            log.info("agent.py を起動しました")
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
    try:
        server = HTTPServer(("0.0.0.0", PORT), Handler)
        server.serve_forever()
    except Exception as e:
        log.critical("サーバー起動失敗: %s", e)
        raise
