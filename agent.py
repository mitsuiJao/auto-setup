"""
agent.py - 生徒PC用エージェントスクリプト
使用方法: python agent.py --login_id <ID> --login_pw <PW> --mkcd_path <PATH> --site_url <URL>
"""

import argparse
import logging
import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

_HERE = (os.path.dirname(sys.executable)
         if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(_HERE, "agent.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)
log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="生徒PC自動起動エージェント")
    parser.add_argument("--login_id", required=True, help="ログインID")
    parser.add_argument("--login_pw", required=True, help="ログインパスワード")
    parser.add_argument("--mkcd_path", required=True, help=".mkcdファイルのパス")
    parser.add_argument("--site_url", required=True, help="サイトURL")
    return parser.parse_args()


def login(driver, site_url, login_id, login_pw):
    driver.get(site_url)
    wait = WebDriverWait(driver, 30)

    # TODO: ログインIDフィールドのセレクタを実際のサイトに合わせて変更してください
    id_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='uid']")))
    id_field.clear()
    id_field.send_keys(login_id)

    # TODO: パスワードフィールドのセレクタを実際のサイトに合わせて変更してください
    pw_field = driver.find_element(By.CSS_SELECTOR, "input[name='pwd']")
    pw_field.clear()
    pw_field.send_keys(login_pw)

    # TODO: ログインボタンのセレクタを実際のサイトに合わせて変更してください
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='order']")
    submit_btn.click()

    # TODO: ログイン後に到達するURLや要素のセレクタを実際のサイトに合わせて変更してください
    wait.until(EC.url_changes(site_url))
    log.info("ログイン成功: %s", login_id)


def open_mkcd(mkcd_path):
    if not os.path.exists(mkcd_path):
        log.error(".mkcdファイルが見つかりません: %s", mkcd_path)
        sys.exit(1)
    os.startfile(mkcd_path)
    log.info(".mkcdファイルを起動: %s", mkcd_path)


def main():
    args = parse_args()
    log.info("agent 起動: login_id=%s site_url=%s mkcd_path=%s", args.login_id, args.site_url, args.mkcd_path)

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # TODO: ChromeDriverのパスが通っていない場合は executable_path を指定してください

    driver = webdriver.Chrome(options=chrome_options)

    try:
        login(driver, args.site_url, args.login_id, args.login_pw)
        time.sleep(2)
        open_mkcd(args.mkcd_path)
        log.info("完了")
    except Exception as e:
        log.exception("予期しないエラー: %s", e)
        driver.quit()
        sys.exit(1)


if __name__ == "__main__":
    main()
