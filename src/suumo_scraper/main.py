import json
import argparse
import sys
import traceback
import random
import time
import os
from typing import Dict, List, Any
from datetime import datetime

# 内部モジュールのインポート
from src.suumo_scraper import config
from src.suumo_scraper.utils.logger import setup_logger
from src.suumo_scraper.sheets.connection import (
    setup_sheet_connection,
    get_urls_from_main_sheet,
)
from src.suumo_scraper.sheets.update import (
    process_url,
    update_property_data,
    batch_update_properties,
    batch_add_new_properties,
)
from src.suumo_scraper.scraper.core import scrape_suumo_property_info
from src.suumo_scraper.scraper.debug import debug_scrape_url

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

            # 重複するURLをフィルタリング
            urls_to_process = [
                url for url in urls_to_process if url and url not in existing_urls
            ]

            if not urls_to_process:
                logger.info("処理対象のURLがありません")
                return result

            # 一括処理: すべてのURLからデータを取得
            new_properties = []

            for i, url in enumerate(urls_to_process):
                try:
                    logger.debug(
                        f"URL({i+1}/{len(urls_to_process)})スクレイピング開始: {url}"
                    )

                    # ランダムな待機時間を設定（サーバー負荷軽減のため）
                    if i > 0:  # 最初のURLは待機なし
                        time.sleep(
                            random.uniform(
                                config.SCRAPING_WAIT_MIN, config.SCRAPING_WAIT_MAX
                            )
                        )

                    # 物件情報を取得
                    property_info = scrape_suumo_property_info(url)
                    property_info["url"] = url  # URLも含めておく

                    # 成功したらリストに追加
                    new_properties.append(property_info)
                    logger.debug(f"スクレイピング成功: {url}")

                except Exception as e:
                    # エラーがあった場合でもリストに追加（エラー情報付き）
                    new_properties.append({"url": url, "error": str(e)})
                    logger.error(f"スクレイピングエラー: {url} - {e}")

            # 取得したデータを一括でスプレッドシートに追加
            if new_properties:
                result, url_to_row = batch_add_new_properties(
                    property_sheet, new_properties, existing_urls, result
                )
                logger.info(f"一括追加完了: {len(new_properties)}件")
            else:
                logger.info("追加する物件情報がありません")

        # 全体更新モード
        elif update_mode == config.MODE_FULL_UPDATE:
            logger.debug(f"全体更新モード開始: 対象URL数={len(existing_urls)}")

            if not existing_urls:
                logger.info("処理対象のURLがありません")
                return result

            # 一括処理: すべてのURLからデータを取得
            all_properties = []

            for i, url in enumerate(existing_urls):
                try:
                    logger.debug(
                        f"URL({i+1}/{len(existing_urls)})スクレイピング開始: {url}"
                    )

                    # ランダムな待機時間を設定（サーバー負荷軽減のため）
                    if i > 0:  # 最初のURLは待機なし
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
                        row = i + 2  # 2行目から開始
                        existing_number = property_sheet.cell(
                            row, config.COLUMNS["number"]
                        ).value
                        if existing_number:
                            property_info["number"] = existing_number
                    except Exception as e:
                        logger.warning(f"既存の通し番号取得エラー: {e}")

                    # 成功したらリストに追加
                    all_properties.append(
                        {"row": i + 2, "data": property_info}  # 2行目から開始
                    )
                    logger.debug(f"スクレイピング成功: {url}")

                except Exception as e:
                    # エラーがあった場合でもリストに追加（エラー情報付き）
                    all_properties.append(
                        {"row": i + 2, "data": {"url": url, "error": str(e)}}
                    )
                    logger.error(f"スクレイピングエラー: {url} - {e}")

            # 取得したデータを一括でスプレッドシートに更新
            if all_properties:
                result = batch_update_properties(property_sheet, all_properties, result)
                result["processed_urls"] = len(all_properties)
                logger.info(f"一括更新完了: {len(all_properties)}件")
            else:
                logger.info("更新する物件情報がありません")

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
