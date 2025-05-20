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
        urls = request_json.get("urls", [])  # 複数URL対応

        # 単一URLが指定されている場合は、それも処理対象に追加
        if url and url not in urls:
            urls.append(url)

        # モードのバリデーション
        if mode not in [config.MODE_NEW_ONLY, config.MODE_FULL_UPDATE]:
            return (jsonify({"error": f"Invalid mode: {mode}"}), 400, headers)

        # 結果を格納するための辞書
        result = {
            "status": "success",
            "processed_urls": 0,
            "success_count": 0,
            "error_count": 0,
            "errors": [],
            "duplicate_urls": [],
            "invalid_urls": [],
        }

        # 複数URLモードと単一URLモードの処理分岐
        if urls and mode == config.MODE_NEW_ONLY:
            # URLごとに処理して結果をマージ
            for input_url in urls:
                if not input_url:
                    continue

                # URLの形式チェック
                if not is_valid_suumo_url(input_url):
                    result["invalid_urls"].append(input_url)
                    continue

                # 個別のURLを処理
                url_result = update_suumo_sheet(update_mode=mode, new_url=input_url)

                # 結果をマージ
                result["processed_urls"] += url_result.get("processed_urls", 0)
                result["success_count"] += url_result.get("success_count", 0)
                result["error_count"] += url_result.get("error_count", 0)

                if url_result.get("status") == "error":
                    result["status"] = "partial_error"
                    result["errors"].append(
                        {
                            "url": input_url,
                            "error_message": url_result.get(
                                "error_message", "不明なエラー"
                            ),
                        }
                    )
        else:
            # 従来通りの処理（単一URLまたは全件更新）
            result = update_suumo_sheet(update_mode=mode, new_url=url)

        # 結果を返す
        return (jsonify(result), 200, headers)

    except Exception as e:
        # エラーハンドリング
        error_response = {"status": "error", "error_message": str(e)}
        return (jsonify(error_response), 500, headers)


def is_valid_suumo_url(url):
    """
    SUUMOのURLが有効かどうかを検証する関数

    Args:
        url: 検証するURL

    Returns:
        bool: 有効なSUUMOのURLであればTrue、そうでなければFalse
    """
    # 空のURLはスキップ
    if not url:
        return False

    # SUUMOの物件URL形式チェック
    is_suumo = "suumo.jp/chintai/" in url

    # jnc_を含むURLは無効
    has_jnc = "/jnc_" in url

    # bc_を含むURLは有効
    has_bc = "/bc_" in url

    return is_suumo and has_bc and not has_jnc
