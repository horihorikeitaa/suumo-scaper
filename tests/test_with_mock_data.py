#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SUUMOスクレイパーの新規登録と更新処理をモックデータで実行するためのテストスクリプト
実際にスクレイピングを行わず、モックデータを使って処理の流れをテストします
"""

import json
import os
import logging
import argparse
from datetime import datetime
from unittest.mock import patch

# 内部モジュールのインポート
from src.suumo_scraper import config
from src.suumo_scraper.utils.logger import setup_logger
from src.suumo_scraper.scraper.core import scrape_suumo_property_info
from src.suumo_scraper.main import update_suumo_sheet

# ロガーの設定
logger = setup_logger()
logger.setLevel(logging.DEBUG)

# モックデータを保存するディレクトリ
MOCK_DIR = "mock_data"
os.makedirs(MOCK_DIR, exist_ok=True)


def create_mock_property_data(property_id, name, rent, layout):
    """
    モック用の物件データを作成

    Args:
        property_id: 物件ID
        name: 物件名
        rent: 家賃
        layout: 間取り

    Returns:
        物件情報の辞書
    """
    return {
        "property_id": property_id,
        "name": name,
        "address": f"東京都新宿区{property_id[-3:]}",
        "access": "JR山手線 新宿駅 徒歩10分",
        "rent": rent,
        "management_fee": "5,000円",
        "deposit": "1ヶ月",
        "key_money": "1ヶ月",
        "layout": layout,
        "area": "25.5m²",
        "direction": "南",
        "building_type": "マンション",
        "age": "築10年",
        "layout_detail": "洋室6.0帖、キッチン2.5帖",
        "structure": "RC",
        "floor": "5階 / 10階建",
        "move_in": "即時可",
        "conditions": "ペット相談可",
        "surrounding": "スーパー（徒歩5分）、コンビニ（徒歩3分）",
        "update_date": datetime.now().strftime("%Y/%m/%d"),
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": f"https://suumo.jp/chintai/bc_{property_id}/",
    }


def generate_mock_properties(count=5):
    """
    モック用の物件データを複数生成

    Args:
        count: 生成する物件数

    Returns:
        物件情報のリスト
    """
    mock_properties = []
    layouts = ["1K", "1DK", "1LDK", "2K", "2DK", "2LDK", "3LDK"]

    for i in range(1, count + 1):
        property_id = f"10043{i:06d}"
        name = f"サンプルマンション{i}"
        rent = f"{(i % 5 + 5) * 10000}円"
        layout = layouts[i % len(layouts)]

        mock_property = create_mock_property_data(property_id, name, rent, layout)
        mock_properties.append(mock_property)

    return mock_properties


def save_mock_data(mock_properties):
    """
    モックデータをJSONファイルに保存

    Args:
        mock_properties: 物件情報のリスト

    Returns:
        保存したファイルのパス
    """
    filename = (
        f"{MOCK_DIR}/mock_properties_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(mock_properties, f, indent=2, ensure_ascii=False)

    logger.info(f"モックデータを保存しました: {filename}")
    return filename


def load_mock_data(filename=None):
    """
    モックデータをJSONファイルから読み込み

    Args:
        filename: 読み込むファイルのパス（Noneの場合は最新のファイルを使用）

    Returns:
        物件情報のリスト
    """
    if filename is None:
        # 最新のモックデータファイルを検索
        mock_files = [
            f for f in os.listdir(MOCK_DIR) if f.startswith("mock_properties_")
        ]
        if not mock_files:
            logger.error("モックデータファイルが見つかりません")
            return None

        latest_file = sorted(mock_files)[-1]
        filename = os.path.join(MOCK_DIR, latest_file)

    try:
        with open(filename, "r", encoding="utf-8") as f:
            mock_properties = json.load(f)

        logger.info(f"モックデータを読み込みました: {filename}")
        return mock_properties
    except Exception as e:
        logger.error(f"モックデータの読み込みエラー: {e}")
        return None


def mock_scrape_property(*args, **kwargs):
    """
    scrape_suumo_property_infoのモック関数

    Args:
        url: スクレイピング対象のURL

    Returns:
        モックの物件情報
    """
    url = args[0]
    property_id = url.split("_")[-1].split("/")[0] if "_" in url else "999999"

    # モックデータから物件IDに一致するデータを検索
    mock_properties = load_mock_data()
    if not mock_properties:
        # モックデータがない場合はその場で生成
        mock_property = create_mock_property_data(
            property_id, f"サンプル物件_{property_id}", "80,000円", "1LDK"
        )
        return mock_property

    # URLからプロパティIDを抽出してモックデータを検索
    for prop in mock_properties:
        if prop["property_id"] == property_id:
            logger.debug(f"モックデータから物件情報を取得: {property_id}")
            return prop

    # 見つからない場合はデフォルトのモックデータを返す
    logger.warning(
        f"モックデータに該当物件がないため、デフォルトデータを使用: {property_id}"
    )
    return create_mock_property_data(
        property_id, f"不明物件_{property_id}", "75,000円", "1K"
    )


class MockGoogleSheet:
    """Google Sheetsのモッククラス"""

    def __init__(self):
        self.data = []
        self.header = [
            "No",
            "URL",
            "物件ID",
            "物件名",
            "住所",
            "アクセス",
            "家賃",
            "管理費",
            "敷金",
            "礼金",
            "間取り",
            "面積",
        ]
        # ヘッダー行を追加
        self.data.append(self.header)
        logger.debug("モックGoogle Sheetを作成しました")

    def col_values(self, col):
        """列の値を取得するモックメソッド"""
        return [row[col - 1] if col - 1 < len(row) else "" for row in self.data]

    def append_row(self, row):
        """行を追加するモックメソッド"""
        self.data.append(row)
        logger.debug(f"行を追加しました: {row}")
        return {"updates": {"updatedCells": len(row)}}

    def update_cell(self, row, col, value):
        """セルを更新するモックメソッド"""
        # 必要に応じて行を拡張
        while len(self.data) <= row:
            self.data.append([""] * len(self.header))

        # 必要に応じて列を拡張
        while len(self.data[row - 1]) <= col - 1:
            self.data[row - 1].append("")

        self.data[row - 1][col - 1] = value
        logger.debug(f"セルを更新しました: ({row}, {col}) = {value}")

    def update(self, values_dict):
        """複数のセルを更新するモックメソッド"""
        for key, value in values_dict.items():
            row = int(key.split("!")[1].split(":")[0][1:])
            col = ord(key.split("!")[1].split(":")[0][0]) - ord("A") + 1
            self.update_cell(row, col, value)

        logger.debug(f"{len(values_dict)}個のセルを更新しました")
        return {"updatedCells": len(values_dict)}

    def cell(self, row, col):
        """セルの値を取得するモックメソッド"""
        if row - 1 < len(self.data) and col - 1 < len(self.data[row - 1]):
            value = self.data[row - 1][col - 1]
        else:
            value = ""

        return type("Cell", (), {"value": value})

    def get_all_values(self):
        """全ての値を取得するモックメソッド"""
        return self.data

    def batch_update(self, data_dict):
        """一括更新のモックメソッド"""
        for range_name, values in data_dict.items():
            start_row = int(range_name.split("!")[1].split(":")[0][1:])
            for i, row_values in enumerate(values):
                for j, value in enumerate(row_values):
                    self.update_cell(start_row + i, j + 1, value)

        logger.debug("一括更新を実行しました")
        return {"totalUpdatedCells": 10}  # 仮の値

    def save_to_file(self, filename=None):
        """モックデータをCSVファイルとして保存"""
        if filename is None:
            filename = (
                f"{MOCK_DIR}/mock_sheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )

        import csv

        with open(filename, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(self.data)

        logger.info(f"モックスプレッドシートをCSVファイルに保存しました: {filename}")
        return filename


class MockSpreadsheet:
    """Google Spreadsheetのモッククラス"""

    def __init__(self, title="モックスプレッドシート"):
        self.title = title
        self.worksheets = {"物件情報": MockGoogleSheet()}
        logger.debug(f"モックスプレッドシートを作成しました: {title}")

    def worksheet(self, name):
        """ワークシートを取得するモックメソッド"""
        if name in self.worksheets:
            return self.worksheets[name]
        else:
            logger.warning(f"ワークシート '{name}' が見つからないため新規作成します")
            self.worksheets[name] = MockGoogleSheet()
            return self.worksheets[name]


class MockGspreadClient:
    """gspreadクライアントのモッククラス"""

    def __init__(self):
        self.spreadsheets = {}
        logger.debug("モックgspreadクライアントを作成しました")

    def open_by_key(self, key):
        """スプレッドシートを取得するモックメソッド"""
        if key not in self.spreadsheets:
            self.spreadsheets[key] = MockSpreadsheet(
                title=f"モックスプレッドシート_{key}"
            )

        return self.spreadsheets[key]


def setup_mock_environment():
    """モック環境をセットアップする"""
    # テスト用のモックデータを生成して保存
    mock_properties = generate_mock_properties(10)
    save_mock_data(mock_properties)

    # モックのGoogle Sheetsクライアントを作成
    mock_client = MockGspreadClient()
    return mock_client


def test_new_property_update(url):
    """
    新規物件追加のテスト

    Args:
        url: 追加対象のURL
    """
    logger.info(f"テスト: 新規物件追加 - {url}")

    # scrape_suumo_property_infoをモック化
    with patch(
        "src.suumo_scraper.sheets.update.scrape_suumo_property_info",
        side_effect=mock_scrape_property,
    ), patch(
        "src.suumo_scraper.main.scrape_suumo_property_info",
        side_effect=mock_scrape_property,
    ), patch(
        "src.suumo_scraper.sheets.connection.setup_sheet_connection",
        return_value=setup_mock_environment(),
    ):

        # 新規物件追加モードで実行
        result = update_suumo_sheet(update_mode=config.MODE_NEW_ONLY, new_url=url)

        # 結果を表示
        print("\n=== 新規物件追加テスト結果 ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        return result


def test_full_update():
    """全物件更新のテスト"""
    logger.info("テスト: 全物件更新")

    # scrape_suumo_property_infoをモック化
    with patch(
        "src.suumo_scraper.sheets.update.scrape_suumo_property_info",
        side_effect=mock_scrape_property,
    ), patch(
        "src.suumo_scraper.main.scrape_suumo_property_info",
        side_effect=mock_scrape_property,
    ), patch(
        "src.suumo_scraper.sheets.connection.setup_sheet_connection",
        return_value=setup_mock_environment(),
    ):

        # スプレッドシートにモックデータを事前に追加
        mock_client = setup_mock_environment()
        mock_sheet = mock_client.open_by_key(config.SPREADSHEET_ID).worksheet(
            config.PROPERTY_SHEET_NAME
        )

        # モックプロパティからURLを抽出してスプレッドシートに追加
        mock_properties = load_mock_data()
        for i, prop in enumerate(mock_properties):
            # スプレッドシートの行を作成（URLだけ含める）
            row_data = [""] * 20
            row_data[0] = str(i + 1)  # 通し番号
            row_data[1] = prop["url"]  # URL
            mock_sheet.append_row(row_data)

        # 全物件更新モードで実行
        result = update_suumo_sheet(update_mode=config.MODE_FULL_UPDATE)

        # 結果を表示
        print("\n=== 全物件更新テスト結果 ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 更新後のスプレッドシートの状態を確認
        mock_sheet.save_to_file()

        return result


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="SUUMOスクレイパーのモックテスト")
    parser.add_argument(
        "--mode",
        choices=["new", "full", "both"],
        default="both",
        help="テストモード（new: 新規物件追加, full: 全物件更新, both: 両方）",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://suumo.jp/chintai/bc_100435000001/",
        help="新規追加テスト用のURL",
    )

    args = parser.parse_args()

    try:
        # テストの実行
        if args.mode in ["new", "both"]:
            test_new_property_update(args.url)

        if args.mode in ["full", "both"]:
            test_full_update()

        logger.info("全てのテストが完了しました")

    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
