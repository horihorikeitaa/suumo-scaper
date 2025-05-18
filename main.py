import json
import argparse
import sys
import traceback
import random
import time
import os
from typing import Dict, List, Any

# 内部モジュールのインポート
import config
from utils.logger import setup_logger
from sheets.connection import setup_sheet_connection, get_urls_from_main_sheet
from sheets.update import process_url, update_property_data
from scraper.core import scrape_suumo_property_info
from scraper.debug import debug_scrape_url

# ロガーの設定
logger = setup_logger()


def update_suumo_sheet(update_mode="new_only", new_url=None):
    """
    物件情報更新処理のメイン関数
    """
    try:
        logger.debug(f"更新処理開始: モード={update_mode}, URL={new_url}")

        # Google Sheetsへの接続
        try:
            client = setup_sheet_connection()
        except RuntimeError as e:
            logger.error(f"Google Sheets接続に失敗しました: {e}")
            return {
                "status": "error",
                "error_message": f"Google Sheets接続エラー: {str(e)}",
                "error_count": 1,
                "processed_urls": 0,
            }

        # スプレッドシートを開く
        try:
            spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
            logger.debug(f"スプレッドシート接続成功: {spreadsheet.title}")
        except Exception as e:
            logger.error(f"スプレッドシートのオープンに失敗しました: {e}")
            return {
                "status": "error",
                "error_message": f"スプレッドシートが見つからないか、アクセスできません: {str(e)}",
                "error_count": 1,
                "processed_urls": 0,
            }

        # 物件情報シートを取得
        try:
            property_sheet = spreadsheet.worksheet(config.PROPERTY_SHEET_NAME)
            logger.debug(f"物件情報シート取得成功")
        except Exception as e:
            logger.error(f"物件情報シートの取得に失敗しました: {e}")
            return {
                "status": "error",
                "error_message": f"物件情報シートが見つかりません: {str(e)}",
                "error_count": 1,
                "processed_urls": 0,
            }

        # 既存のURLを取得 (B列2行目から)
        try:
            existing_urls = property_sheet.col_values(config.COLUMNS["url"])[
                1:
            ]  # ヘッダー行を除く
            logger.debug(f"既存URL数: {len(existing_urls)}")
        except Exception as e:
            logger.error(f"既存URLの取得に失敗しました: {e}")
            return {
                "status": "error",
                "error_message": f"スプレッドシートからURLを取得できません: {str(e)}",
                "error_count": 1,
                "processed_urls": 0,
            }

        # 結果を格納する辞書
        result = {
            "status": "success",
            "update_mode": update_mode,
            "processed_urls": 0,
            "success_count": 0,
            "error_count": 0,
            "errors": [],
        }

        # 新規URL追加モード
        if update_mode == config.MODE_NEW_ONLY:
            urls_to_process = []

            if new_url:  # コマンドラインから指定されたURL
                urls_to_process.append(new_url)
                logger.debug(f"コマンドラインから指定されたURL: {new_url}")
            else:
                # mainシートからURLリストを取得
                urls_to_process = get_urls_from_main_sheet(spreadsheet)

            # バッチ処理：各URLを処理
            for url in urls_to_process:
                try:
                    result = process_url(url, property_sheet, existing_urls, result)
                    # 処理後に既存URLリストに追加して重複チェック用データを更新
                    if url and url not in existing_urls:
                        existing_urls.append(url)
                except Exception as url_error:
                    # URLごとの処理エラーを記録して続行
                    if "Quota exceeded" in str(url_error) or "429" in str(url_error):
                        logger.warning(
                            f"APIレート制限に達しました。一時停止します: {url_error}"
                        )
                        time.sleep(
                            config.API_RATE_LIMIT_WAIT
                        )  # APIレート制限に達した場合は待機

                        # 再試行処理
                        retry_success = False
                        for retry in range(config.API_RETRY_COUNT):
                            try:
                                # 再試行
                                result = process_url(
                                    url, property_sheet, existing_urls, result
                                )
                                if url and url not in existing_urls:
                                    existing_urls.append(url)
                                retry_success = True
                                logger.debug(
                                    f"URL処理再試行成功（{retry+1}回目）: {url}"
                                )
                                break
                            except Exception as retry_error:
                                logger.warning(
                                    f"URL処理再試行失敗（{retry+1}/{config.API_RETRY_COUNT}）: {retry_error}"
                                )
                                if "Quota exceeded" in str(retry_error) or "429" in str(
                                    retry_error
                                ):
                                    time.sleep(
                                        config.API_RATE_LIMIT_WAIT * (retry + 1)
                                    )  # 待機時間を増やす
                                else:
                                    time.sleep(config.API_WRITE_INTERVAL)

                        if retry_success:
                            continue
                        else:
                            logger.error(f"再試行後もエラー発生: {url}")

                    result["status"] = "partial_error"
                    result["error_count"] += 1
                    result["errors"].append(
                        {"url": url, "error_message": str(url_error)}
                    )
                    logger.error(f"URL処理中にエラー発生: {url_error}")

        # 全体更新モード
        elif update_mode == config.MODE_FULL_UPDATE:
            logger.debug(f"全体更新モード開始: 対象URL数={len(existing_urls)}")

            # 物件情報シートの全URLを処理
            for i, url in enumerate(existing_urls, start=2):  # 2行目から開始
                try:
                    logger.debug(f"URL({i-1}/{len(existing_urls)})処理開始: {url}")

                    # ランダムな待機時間を設定
                    time.sleep(
                        random.uniform(
                            config.SCRAPING_WAIT_MIN, config.SCRAPING_WAIT_MAX
                        )
                    )

                    # 物件情報を取得
                    property_info = scrape_suumo_property_info(url)
                    property_info["url"] = url  # URLも含めておく

                    # 既存の通し番号を保持
                    try:
                        existing_number = property_sheet.cell(
                            i, config.COLUMNS["number"]
                        ).value
                        if existing_number:
                            property_info["number"] = existing_number
                    except Exception as e:
                        logger.warning(f"既存の通し番号取得エラー: {e}")

                    # 物件情報を更新
                    result = update_property_data(
                        property_sheet, i, property_info, result
                    )
                    result["processed_urls"] += 1

                except Exception as e:
                    if "Quota exceeded" in str(e) or "429" in str(e):
                        logger.warning(
                            f"APIレート制限に達しました。一時停止します: {e}"
                        )
                        time.sleep(
                            config.API_RATE_LIMIT_WAIT * 2
                        )  # APIレート制限に達した場合は長めに待機

                        # 再試行処理
                        retry_success = False
                        for retry in range(config.API_RETRY_COUNT):
                            try:
                                # 再試行（スクレイピングはスキップ、直前の物件情報を使用）
                                if (
                                    "property_info" in locals()
                                ):  # 物件情報が取得できていれば再利用
                                    result = update_property_data(
                                        property_sheet, i, property_info, result
                                    )
                                    result["processed_urls"] += 1
                                    retry_success = True
                                    logger.debug(
                                        f"URL更新再試行成功（{retry+1}回目）: {url}"
                                    )
                                    break
                                else:
                                    # 物件情報が取得できていない場合は再取得
                                    property_info = scrape_suumo_property_info(url)
                                    property_info["url"] = url
                                    result = update_property_data(
                                        property_sheet, i, property_info, result
                                    )
                                    result["processed_urls"] += 1
                                    retry_success = True
                                    break
                            except Exception as retry_error:
                                logger.warning(
                                    f"URL更新再試行失敗（{retry+1}/{config.API_RETRY_COUNT}）: {retry_error}"
                                )
                                if "Quota exceeded" in str(retry_error) or "429" in str(
                                    retry_error
                                ):
                                    time.sleep(
                                        config.API_RATE_LIMIT_WAIT * (retry + 2)
                                    )  # 待機時間を増やす
                                else:
                                    time.sleep(config.API_WRITE_INTERVAL)

                        if retry_success:
                            continue
                        else:
                            logger.error(f"再試行後もエラー発生: {url}")

                    result["status"] = "partial_error"
                    result["error_count"] += 1
                    result["errors"].append({"url": url, "error_message": str(e)})
                    logger.error(f"URL更新中にエラー発生: {e}")

        # 処理結果の返却
        logger.debug(f"処理完了: {result}")
        return result

    except Exception as main_error:
        # メイン処理でのエラーをログに記録
        logger.error(f"メイン処理でエラー発生: {main_error}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "error_message": str(main_error),
            "error_count": 1,
            "processed_urls": 0,
        }


def main():
    """
    メイン処理
    """
    parser = argparse.ArgumentParser(description="SUUMO物件情報取得ツール")
    parser.add_argument(
        "--mode",
        type=str,
        default=config.MODE_NEW_ONLY,
        choices=[config.MODE_NEW_ONLY, config.MODE_FULL_UPDATE],
        help="実行モード（new_only: 新規物件のみ追加, full_update: 全物件の情報更新）",
    )
    parser.add_argument("--url", type=str, help="単一のURLを処理する場合に指定")
    parser.add_argument(
        "--debug", action="store_true", help="デバッグモード（詳細なログを出力）"
    )
    parser.add_argument(
        "--debug-html",
        type=str,
        help="サンプルHTMLファイルをデバッグ（ファイルパスまたはURL）",
    )

    args = parser.parse_args()

    if args.debug:
        import logging

        # ルートロガーを設定
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("デバッグモードで起動")

    # デバッグHTMLモード
    if args.debug_html:
        logger.info(f"デバッグモード: {args.debug_html}")
        try:
            # ローカルファイルかURLかを判断
            if os.path.exists(args.debug_html):
                debug_url = f"file://{os.path.abspath(args.debug_html)}"
            else:
                debug_url = args.debug_html

            # デバッグ用のスクレイピング関数を実行
            result = debug_scrape_url(debug_url)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(0)
        except Exception as e:
            logger.error(f"デバッグ処理中にエラーが発生しました: {e}")
            traceback.print_exc()
            sys.exit(1)

    # 通常モード
    try:
        # メインモードの処理を実行
        result = update_suumo_sheet(args.mode, args.url)

        # 処理結果を出力
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # エラーがあった場合は異常終了コードを返す
        if result["status"] == "error":
            logger.error(f"処理エラー: {result.get('error_message', '未知のエラー')}")
            sys.exit(1)
        elif result["status"] == "partial_error":
            logger.warning(f"一部エラーあり: {result['error_count']}件のエラーが発生")
            # 部分的なエラーは成功として扱う（警告のみ）
            sys.exit(0)
        else:
            logger.info(
                f"処理成功: {result['processed_urls']}件処理、{result['success_count']}件成功"
            )
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("ユーザーによる中断")
        sys.exit(130)  # SIGINT (Ctrl+C) の標準的な終了コード
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"致命的なエラーが発生しました: {e}")
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("ユーザーによる処理中断")
        sys.exit(130)  # SIGINT (Ctrl+C) の標準的な終了コード
