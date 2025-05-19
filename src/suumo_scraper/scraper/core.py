import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import os
from datetime import datetime
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from src.suumo_scraper import config
from src.suumo_scraper.scraper.parser_factory import create_parser


def create_session():
    """
    リトライ機能を持つセッションを作成する

    Returns:
        設定済みのrequestsセッション
    """
    session = requests.Session()

    # リトライ設定
    retry_strategy = Retry(
        total=config.MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # ヘッダー設定
    session.headers.update(config.REQUEST_HEADERS)

    return session


def scrape_suumo_property_info(url):
    """
    SUUMOの物件ページから詳細情報を取得する関数

    Args:
        url: スクレイピング対象のURL

    Returns:
        物件情報を格納した辞書
    """
    try:
        # ランダムな待機時間を設定
        time.sleep(random.uniform(config.SCRAPING_WAIT_MIN, config.SCRAPING_WAIT_MAX))

        logging.debug(f"スクレイピング開始: {url}")

        # ファイルURLの場合はローカルファイルを読み込む
        if url.startswith("file://"):
            local_path = url.replace("file://", "")
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                logging.debug(f"ローカルファイルから読み込み: {local_path}")
            except Exception as e:
                logging.error(f"ローカルファイルの読み込みに失敗: {e}")
                raise

            soup = BeautifulSoup(html_content, "html.parser")
        else:
            # セッションを作成
            session = create_session()

            # 通常のURLの場合はリクエストを送信 - タイムアウト設定を分離して明示的に指定
            try:
                # まずHTTPSで試行
                r = session.get(
                    url,
                    timeout=(
                        10,
                        config.REQUEST_TIMEOUT,
                    ),  # (接続タイムアウト, 読み込みタイムアウト)
                    allow_redirects=True,
                    verify=True,  # SSL証明書の検証
                )
                r.raise_for_status()
            except (
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
            ) as e:
                # SSLエラーやHTTPS接続エラーが発生した場合、HTTPで再試行
                logging.warning(f"HTTPS接続エラー、HTTPで再試行します: {e}")
                r = session.get(
                    url.replace("https://", "http://"),
                    timeout=(10, config.REQUEST_TIMEOUT),
                    allow_redirects=True,
                    verify=False,  # SSL証明書の検証を無効化
                )
                r.raise_for_status()

            # HTTPステータスコードとURLをログに記録（リダイレクトの確認）
            if r.history:
                redirect_chain = " -> ".join(
                    [f"{resp.status_code}: {resp.url}" for resp in r.history]
                )
                logging.debug(
                    f"リダイレクト経路: {redirect_chain} -> {r.status_code}: {r.url}"
                )

            # レスポンスの内容を取得し、デバッグのためにHTMLを保存
            html_content = r.content
            save_html_for_debug(url, html_content)

            soup = BeautifulSoup(html_content, "html.parser")

        # パターン判定とパーサー作成
        parser = create_parser(soup, url)

        # 物件情報を解析
        property_info = parser.parse()

        # デバッグ出力
        logging.debug(f"物件情報の解析完了: {property_info['property_id']}")

        return property_info

    except Exception as e:
        logging.error(f"物件情報の取得に失敗: {url}, エラー: {e}")
        # 最小限の情報だけを含む辞書を返す
        return {
            "property_id": url.split("_")[-1].split("/")[0] if "_" in url else "",
            "name": "",
            "error": str(e),
        }


def save_html_for_debug(url, html_content):
    """
    デバッグ用にHTMLを保存する

    Args:
        url: スクレイピング対象のURL
        html_content: HTML内容

    Returns:
        保存したファイルパス
    """
    # 本番環境ではHTMLを保存しない設定を追加
    if not config.SAVE_DEBUG_HTML:
        logging.debug("デバッグHTMLの保存をスキップ（設定により無効）")
        return None

    debug_dir = "debug_data"
    os.makedirs(debug_dir, exist_ok=True)

    # 古いファイルを削除する（オプション）
    if config.MAX_DEBUG_FILES > 0:
        try:
            files = sorted(
                [
                    os.path.join(debug_dir, f)
                    for f in os.listdir(debug_dir)
                    if f.endswith(".html")
                ],
                key=os.path.getctime,
            )
            # 最大ファイル数を超えた場合、古いファイルを削除
            if len(files) >= config.MAX_DEBUG_FILES:
                for old_file in files[: len(files) - config.MAX_DEBUG_FILES + 1]:
                    os.remove(old_file)
                    logging.debug(f"古いデバッグファイルを削除: {old_file}")
        except Exception as e:
            logging.warning(f"古いデバッグファイルの削除に失敗: {e}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    property_id = url.split("_")[-1].split("/")[0] if "_" in url else "unknown"
    html_file = f"{debug_dir}/suumo_{property_id}_{timestamp}.html"

    with open(html_file, "wb") as f:
        f.write(html_content)

    logging.debug(f"HTML保存完了: {html_file}")
    return html_file
