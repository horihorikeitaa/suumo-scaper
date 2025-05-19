import gspread
from google.oauth2.service_account import Credentials
import logging
import json
import os
from src.suumo_scraper import config


def setup_sheet_connection():
    """
    Google Spreadsheetsに接続するための関数
    ローカルファイルまたは環境変数から認証情報を取得
    """
    try:
        # 環境変数から認証情報を取得する方法を追加
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
            # 環境変数からJSON文字列を取得してJSONオブジェクトに変換
            creds_json = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
            creds = Credentials.from_service_account_info(
                creds_json, scopes=config.SCOPES
            )
            logging.info("環境変数から認証情報を取得しました")
        elif os.path.exists(config.CREDS_FILE_PATH):
            # ローカルファイルから認証情報を取得
            creds = Credentials.from_service_account_file(
                config.CREDS_FILE_PATH, scopes=config.SCOPES
            )
            logging.info(
                f"ファイルから認証情報を取得しました: {config.CREDS_FILE_PATH}"
            )
        else:
            # デフォルトの認証情報（Cloud Run上で使用するアプリケーションデフォルト認証情報）
            try:
                # このパスはCloud Runでマウントされた認証情報
                creds = Credentials.from_service_account_file(
                    "/secrets/credentials.json", scopes=config.SCOPES
                )
                logging.info("Cloud Runのマウントされた認証情報を使用します")
            except FileNotFoundError:
                # アプリケーションデフォルト認証情報を試す
                import google.auth

                creds, _ = google.auth.default(scopes=config.SCOPES)
                logging.info("アプリケーションデフォルト認証情報を使用します")

        # gspreadクライアントの初期化
        client = gspread.authorize(creds)

        return client
    except FileNotFoundError as e:
        logging.error(f"認証ファイルが見つかりません: {config.CREDS_FILE_PATH}")
        logging.error(f"エラー詳細: {e}")
        raise RuntimeError(
            f"認証ファイルが見つかりません: {config.CREDS_FILE_PATH}"
        ) from e
    except Exception as e:
        logging.error(f"スプレッドシート接続エラー: {e}")
        raise RuntimeError(f"スプレッドシート接続に失敗しました: {e}") from e


def get_urls_from_main_sheet(spreadsheet):
    """
    メインシートからURLリストを取得する関数

    Returns:
        URLのリスト
    """
    try:
        main_sheet = spreadsheet.worksheet(config.MAIN_SHEET_NAME)
        cell_range = main_sheet.range(config.NEW_URL_RANGE)
        urls = [cell.value for cell in cell_range if cell.value]
        logging.debug(f"{config.MAIN_SHEET_NAME}シートから取得したURL: {len(urls)}件")
        return urls
    except Exception as e:
        logging.error(f"{config.MAIN_SHEET_NAME}シートからのURL取得エラー: {e}")
        return []
