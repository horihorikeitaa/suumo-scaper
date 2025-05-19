"""
SUUMOスクレイピングの設定ファイル
"""

# スプレッドシートの設定
SPREADSHEET_ID = "1iAdgFDYd7Tl441za4Afm3ybSCZk0vsIiia59Z77SeOE"
PROPERTY_SHEET_NAME = "物件情報"
MAIN_SHEET_NAME = "main"
NEW_URL_RANGE = "B9:B18"  # 新規URL入力範囲

# 認証関連の設定
CREDS_FILE_PATH = "suumo-scraper-460206-6734b711c3fa.json"
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# スクレイピング設定
SCRAPING_WAIT_MIN = 3  # 最小待機時間（秒）
SCRAPING_WAIT_MAX = 5  # 最大待機時間（秒）
REQUEST_TIMEOUT = 60  # リクエストタイムアウト（秒）- タイムアウトを60秒に延長
MAX_RETRIES = 3  # 最大リトライ回数
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Referer": "https://suumo.jp/",  # リファラーを追加
}

# Google Sheets API制限対策
API_WRITE_INTERVAL = (
    5  # APIリクエスト間の通常待機時間（秒）- 連続リクエストを避けるために長めに設定
)
API_RATE_LIMIT_WAIT = 45  # レート制限エラー発生時の初期待機時間（秒）
API_RETRY_COUNT = 5  # エラー発生時の最大再試行回数 - レート制限が厳しい場合のために増加
ESSENTIAL_COLUMNS = [
    "property_id",
    "name",
    "address",
    "access",
    "rent",
    "layout",
    "area",
    "update_time",
    "management_fee",  # 管理費も重要情報として追加
    "deposit",  # 敷金も重要情報として追加
    "key_money",  # 礼金も重要情報として追加
]  # エラー時に優先的に更新する重要カラム

# ログ設定
LOG_LEVEL = "INFO"  # ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

# スプレッドシートのカラムマッピング（物件情報シート）
COLUMNS = {
    "number": 1,  # #（通し番号）
    "url": 2,  # URL
    "property_id": 3,  # 物件ID
    "name": 4,  # 物件名
    "address": 5,  # 住所
    "access": 6,  # アクセス
    "rent": 7,  # 家賃
    "management_fee": 8,  # 管理費・共益費
    "deposit": 9,  # 敷金
    "key_money": 10,  # 礼金
    "layout": 11,  # 間取り
    "area": 12,  # 専有面積
    "direction": 13,  # 向き
    "building_type": 14,  # 建物種別
    "age": 15,  # 築年数
    "layout_detail": 16,  # 間取り詳細
    "structure": 17,  # 構造
    "floor": 18,  # 階数
    "move_in": 19,  # 入居
    "conditions": 20,  # 条件
    "surrounding": 21,  # 周辺情報
    "update_date": 22,  # 情報更新日
    "update_time": 23,  # update_time
}

# 各モードの設定
MODE_NEW_ONLY = "new_only"
MODE_FULL_UPDATE = "full_update"

# デバッグHTMLの保存設定
SAVE_DEBUG_HTML = False  # 本番環境ではFalse、開発環境ではTrue
MAX_DEBUG_FILES = 10  # 保存する最大ファイル数（0は無制限）
