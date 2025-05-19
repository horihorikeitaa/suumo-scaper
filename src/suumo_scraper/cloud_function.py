import json
import functions_framework
from flask import jsonify
from src.suumo_scraper.main import update_suumo_sheet
from src.suumo_scraper import config


@functions_framework.http
def suumo_scraper(request):
    """
    Google Cloud Functionsのエントリーポイント
    HTTPリクエストを受け取り、SUUMOスクレイピングを実行する
    GASからリクエストが送信されることを想定
    """
    # CORSヘッダーを設定
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "3600",
    }

    # OPTIONSリクエスト（プリフライトリクエスト）への対応
    if request.method == "OPTIONS":
        return ("", 204, headers)

    # POSTリクエスト以外は拒否
    if request.method != "POST":
        return (jsonify({"error": "Method not allowed"}), 405, headers)

    try:
        # リクエストのJSONデータを取得
        request_json = request.get_json(silent=True)

        if not request_json:
            return (jsonify({"error": "No JSON data provided"}), 400, headers)

        # パラメータの取得
        mode = request_json.get("mode", config.MODE_NEW_ONLY)
        url = request_json.get("url", None)

        # モードのバリデーション
        if mode not in [config.MODE_NEW_ONLY, config.MODE_FULL_UPDATE]:
            return (jsonify({"error": f"Invalid mode: {mode}"}), 400, headers)

        # スクレイピング実行
        result = update_suumo_sheet(update_mode=mode, new_url=url)

        # 結果を返す
        return (jsonify(result), 200, headers)

    except Exception as e:
        # エラーハンドリング
        error_response = {"status": "error", "error_message": str(e)}
        return (jsonify(error_response), 500, headers)
