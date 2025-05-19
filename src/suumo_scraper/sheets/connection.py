import gspread
from google.oauth2.service_account import Credentials
import logging
from src.suumo_scraper import config


def setup_sheet_connection():
    """
    Google Spreadsheetsに接続するための関数
    """
    try:
        # 認証情報の設定
        creds = Credentials.from_service_account_file(
            config.CREDS_FILE_PATH, scopes=config.SCOPES
        )

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
