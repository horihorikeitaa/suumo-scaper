import time
import logging
import config
from typing import Dict, List, Any


def update_property_data(
    property_sheet, row: int, property_info: Dict[str, Any], result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    物件情報をスプレッドシートに更新する共通関数

    Args:
        property_sheet: 物件情報シート
        row: 更新する行
        property_info: 物件情報のデータ
        result: 結果を格納する辞書

    Returns:
        更新された結果辞書
    """
    try:
        # エラーチェック
        if "error" in property_info:
            result["status"] = "partial_error"
            result["error_count"] += 1
            result["errors"].append(
                {
                    "url": property_info.get("url", "Unknown URL"),
                    "error_message": property_info.get("error", "未知のエラー"),
                }
            )
            logging.error(f"物件情報取得エラー: {property_info.get('error', '')}")
            return result

        # 通し番号を設定（新規追加の場合）
        if "number" not in property_info and row > 2:
            try:
                # 前の行の通し番号を取得して+1する
                prev_number = property_sheet.cell(
                    row - 1, config.COLUMNS["number"]
                ).value
                if prev_number and prev_number.isdigit():
                    property_info["number"] = str(int(prev_number) + 1)
                else:
                    property_info["number"] = str(row - 1)  # 行番号-1を通し番号とする
            except Exception as e:
                logging.warning(f"通し番号の設定に失敗: {e}")
                property_info["number"] = str(row - 1)

        # 更新データを準備
        # 値だけを先に用意して、一度にまとめて更新する形式に変更
        row_data = []
        key_to_index = {}  # カラム名とインデックスのマッピング

        # 最大列番号を特定
        max_col = max(col for col in config.COLUMNS.values())

        # 空のリストを作成（最大列数分）
        for _ in range(max_col):
            row_data.append("")

        # データをセット
        for key, col in config.COLUMNS.items():
            key_to_index[key] = col - 1  # 0-indexedに変換
            if (
                key != "url" and key in property_info
            ):  # URLは既に書き込み済みの場合があるため除外
                row_data[col - 1] = property_info.get(key, "")
            elif key == "url" and "url" in property_info:
                row_data[col - 1] = property_info["url"]

        # エクスポネンシャルバックオフの実装関数
        def exponential_backoff_retry(
            func,
            max_retries=config.API_RETRY_COUNT,
            initial_wait=config.API_RATE_LIMIT_WAIT,
        ):
            """
            エクスポネンシャルバックオフを使用して関数を再試行する

            Args:
                func: 実行する関数
                max_retries: 最大再試行回数
                initial_wait: 初期待機時間（秒）

            Returns:
                関数の実行結果またはNone（すべての再試行が失敗した場合）
            """
            retry_count = 0
            wait_time = initial_wait

            while retry_count <= max_retries:
                try:
                    if retry_count > 0:
                        logging.info(
                            f"再試行 {retry_count}/{max_retries}... 待機時間: {wait_time}秒"
                        )
                        time.sleep(wait_time)
                    return func()
                except Exception as e:
                    is_rate_limit = "Quota exceeded" in str(e) or "429" in str(e)
                    retry_count += 1

                    if retry_count > max_retries:
                        logging.error(f"最大再試行回数に達しました: {e}")
                        return None

                    # レート制限エラーの場合は待機時間を長くする
                    if is_rate_limit:
                        wait_time = min(wait_time * 2, 300)  # 最大5分まで
                    else:
                        wait_time = min(
                            wait_time * 1.5, 120
                        )  # その他のエラーは1.5倍、最大2分

            return None

        # バッチ更新方式1: 行全体を一度に更新（最も効率的）
        try:
            # APIリクエスト前に短時間の待機を設定して連続リクエストを避ける
            time.sleep(config.API_WRITE_INTERVAL)

            # データの長さを確認してセル範囲を調整
            # データの長さを確認してセル範囲を調整（最大列数をCOLUMNSの最大値に合わせる）
            max_column_index = max(config.COLUMNS.values())
            last_column = chr(
                64 + min(max_column_index, 26)
            )  # A-Zまでの範囲（最大26列）

            # 26列以上の場合の対応
            if max_column_index > 26:
                last_column = "A" + chr(64 + (max_column_index - 26))  # AA, AB, ...

            # 一度に行全体を更新する関数
            def update_whole_row():
                try:
                    # 更新するデータの長さを確認してログ出力
                    logging.debug(
                        f"更新するデータ長: {len(row_data)}, 最大列インデックス: {max_column_index}"
                    )
                    response = property_sheet.update(
                        f"A{row}:{last_column}{row}",
                        [row_data[:max_column_index]],
                        value_input_option="RAW",
                    )
                    return response
                except Exception as e:
                    logging.error(f"行更新エラーの詳細: {str(e)}")
                    # 更新しようとしている行データをログに出力（デバッグ用）
                    logging.debug(f"行データ: {row_data[:max_column_index]}")
                    logging.debug(f"セル範囲: A{row}:{last_column}{row}")
                    raise

            result_update = exponential_backoff_retry(update_whole_row)

            if result_update is not None:
                logging.debug(f"物件情報一括更新成功（行: {row}）")
                result["success_count"] += 1
                return result
        except Exception as update_error:
            logging.warning(
                f"行全体の更新に失敗、バッチ更新に切り替えます: {update_error}"
            )

        # バッチ更新方式2: 複数の値をバッチで更新
        try:
            # バッチ更新用のデータを準備
            batch_data = []
            ranges_to_update = []

            # すべての値をバッチデータに追加
            for key, col in config.COLUMNS.items():
                if key in property_info:
                    # 列番号から列文字に変換（26列以上対応）
                    if col <= 26:
                        col_letter = chr(64 + col)  # 1→A, 2→B, ...
                    else:
                        col_letter = "A" + chr(64 + (col - 26))  # 27→AA, 28→AB, ...

                    cell_ref = f"{col_letter}{row}"
                    value = property_info[key]
                    ranges_to_update.append((cell_ref, value))

            # 同時に更新するセル数を制限（Google Sheets APIの制限に対応）
            max_cells_per_batch = 50
            for i in range(0, len(ranges_to_update), max_cells_per_batch):
                batch_chunk = ranges_to_update[i : i + max_cells_per_batch]
                batch_data = []

                for cell_ref, value in batch_chunk:
                    batch_data.append({"range": cell_ref, "values": [[value]]})

            # バッチ更新を実行する関数
            def update_batch():
                try:
                    response = property_sheet.batch_update(batch_data)
                    return response
                except Exception as e:
                    logging.error(f"バッチ更新エラーの詳細: {str(e)}")
                    # バッチデータの内容をログに出力（デバッグ用）
                    logging.debug(f"バッチデータ: {batch_data}")
                    raise

            time.sleep(config.API_WRITE_INTERVAL)
            result_batch = exponential_backoff_retry(update_batch)

            if result_batch is None:
                raise Exception("バッチ更新に失敗しました")

            logging.debug(f"バッチ方式での更新成功（行: {row}）")
            result["success_count"] += 1
            return result

        except Exception as e:
            logging.error(f"データ更新エラー（行: {row}）: {e}")
            result["error_count"] += 1
            result["status"] = "partial_error"
            result["errors"].append(
                {
                    "url": property_info.get("url", "Unknown URL"),
                    "error_message": str(e),
                }
            )

            # エラー発生時、最低限の重要情報だけでも更新を試みる
            try:
                essential_updates = []
                for key in config.ESSENTIAL_COLUMNS:
                    if key in property_info and key in config.COLUMNS:
                        col = config.COLUMNS[key]
                        if col <= 26:
                            col_letter = chr(64 + col)
                        else:
                            col_letter = "A" + chr(64 + (col - 26))

                        cell_ref = f"{col_letter}{row}"
                        value = property_info[key]
                        essential_updates.append((cell_ref, value))

                # 重要情報だけをバッチ更新
                if essential_updates:
                    batch_essential = []
                    for cell_ref, value in essential_updates:
                        batch_essential.append({"range": cell_ref, "values": [[value]]})

                    def update_essential_batch():
                        try:
                            response = property_sheet.batch_update(batch_essential)
                            return response
                        except Exception as e:
                            logging.error(f"重要情報更新エラー: {e}")
                            raise

                    time.sleep(config.API_WRITE_INTERVAL)
                    exponential_backoff_retry(update_essential_batch)
                    logging.info(f"重要情報の更新に成功（行: {row}）")
                    result["status"] = "partial_success"
            except Exception as essential_error:
                logging.error(f"重要情報更新も失敗（行: {row}）: {essential_error}")
                # セルごとの更新を試みる
                try:
                    for key in ["property_id", "name"]:  # 最小限の識別情報
                        if key in property_info and key in config.COLUMNS:
                            col = config.COLUMNS[key]
                            if col <= 26:
                                col_letter = chr(64 + col)
                            else:
                                col_letter = "A" + chr(64 + (col - 26))

                            cell_ref = f"{col_letter}{row}"
                            value = property_info[key]

                            def update_single_cell():
                                try:
                                    response = property_sheet.update(
                                        cell_ref, [[value]], value_input_option="RAW"
                                    )
                                    return response
                                except Exception as e:
                                    logging.error(f"セル更新エラー ({cell_ref}): {e}")
                                    raise

                            time.sleep(config.API_WRITE_INTERVAL)
                            exponential_backoff_retry(update_single_cell)
                    logging.info(f"最小限の識別情報更新に成功（行: {row}）")
                except Exception as cell_error:
                    logging.error(f"すべての更新方法が失敗（行: {row}）: {cell_error}")

    except Exception as final_error:
        logging.error(f"予期せぬエラー（行: {row}）: {final_error}")
        result["error_count"] += 1
        result["status"] = "error"
        result["errors"].append(
            {
                "url": property_info.get("url", "Unknown URL"),
                "error_message": str(final_error),
            }
        )

    return result


def process_url(
    url: str, property_sheet, existing_urls: List[str], result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    単一のURLを処理する関数

    Args:
        url: 処理するURL
        property_sheet: 物件情報シート
        existing_urls: 既存のURL一覧
        result: 結果を格納する辞書

    Returns:
        更新された結果辞書
    """
    try:
        if not url:
            logging.debug("URLが空です")
            return result

        # URLの重複確認
        if url in existing_urls:
            logging.debug(f"URLはすでに登録済み: {url}")
            return result

        logging.debug(f"新規URL処理開始: {url}")

        # 物件情報シートの最終行に追加
        next_row = len(existing_urls) + 2

        # URLをシートに追加（レート制限エラー対策）
        update_success = False
        retry_count = 0
        while not update_success and retry_count < config.API_RETRY_COUNT:
            try:
                property_sheet.update_cell(next_row, config.COLUMNS["url"], url)
                logging.debug(f"URL追加: 行={next_row}, URL={url}")
                update_success = True
                time.sleep(config.API_WRITE_INTERVAL)  # 書き込み後の待機
            except Exception as url_error:
                retry_count += 1
                if "Quota exceeded" in str(url_error) or "429" in str(url_error):
                    wait_time = config.API_RATE_LIMIT_WAIT * (retry_count)
                    logging.warning(
                        f"URL追加時にAPIレート制限エラー発生。待機します（{wait_time}秒）: {url_error}"
                    )
                    time.sleep(wait_time)
                else:
                    logging.error(f"URL追加エラー（{retry_count}回目）: {url_error}")
                    time.sleep(config.API_WRITE_INTERVAL)

                if retry_count >= config.API_RETRY_COUNT:
                    logging.error(
                        f"URL追加の最大再試行回数（{config.API_RETRY_COUNT}回）に達しました。次のURLに進みます。"
                    )
                    result["status"] = "partial_error"
                    result["error_count"] += 1
                    result["errors"].append(
                        {
                            "url": url,
                            "error_message": f"URL追加エラー: {str(url_error)}",
                        }
                    )
                    return result

        # ここで物件情報取得の関数をインポート（循環参照回避のため）
        from scraper.core import scrape_suumo_property_info

        # 物件情報を取得
        property_info = scrape_suumo_property_info(url)
        property_info["url"] = url  # URLも含めておく

        # 物件情報を更新
        result = update_property_data(property_sheet, next_row, property_info, result)
        result["processed_urls"] += 1

        return result
    except Exception as e:
        result["status"] = "partial_error"
        result["error_count"] += 1
        result["errors"].append({"url": url, "error_message": str(e)})
        logging.error(f"URL処理中にエラー発生: {e}")
        return result
