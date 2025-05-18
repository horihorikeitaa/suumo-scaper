import json
import os
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from utils.text_processor import (
    extract_number_from_text,
    process_currency,
    process_age,
    process_area,
    clean_text,
)


# パターン定義の読み込み
def load_patterns():
    """
    patterns.jsonからパターン定義を読み込む
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    patterns_file = os.path.join(current_dir, "patterns.json")
    with open(patterns_file, "r", encoding="utf-8") as f:
        return json.load(f)


class BaseParser:
    """
    パーサーの基底クラス
    """

    def __init__(self, pattern_name, soup, url):
        """
        パーサーの初期化

        Args:
            pattern_name: パターン名
            soup: BeautifulSoupオブジェクト
            url: スクレイピング対象のURL
        """
        self.pattern_name = pattern_name
        self.soup = soup
        self.url = url

        # パターン定義の読み込み
        patterns = load_patterns()
        if pattern_name not in patterns:
            raise ValueError(f"Unknown pattern: {pattern_name}")

        self.config = patterns[pattern_name]
        self.selectors = self.config.get("selectors", {})
        self.selector_types = self.config.get("selector_types", {})
        self.processor_rules = self.config.get("processor_rules", {})

    def get_element(self, key):
        """
        指定されたキーのセレクタで要素を取得

        Args:
            key: セレクタのキー

        Returns:
            要素が見つかった場合はBeautifulSoupの要素、見つからなかった場合はNone
        """
        if key not in self.selectors:
            logging.warning(f"セレクタが定義されていません: {key}")
            return None

        selector = self.selectors[key]
        selector_type = self.selector_types.get(key, "single")

        if selector_type == "multiple":
            return self.soup.select(selector)
        else:
            return self.soup.select_one(selector)

    def get_text(self, key):
        """
        指定されたキーのセレクタで要素のテキストを取得

        Args:
            key: セレクタのキー

        Returns:
            要素のテキスト、要素が見つからなかった場合は空文字列
        """
        element = self.get_element(key)

        if element is None:
            return ""

        selector_type = self.selector_types.get(key, "single")

        if selector_type == "multiple":
            # 複数要素の場合はテキストをリストとして取得
            return [clean_text(el.text) for el in element]
        else:
            # 単一要素の場合はテキストを文字列として取得
            return clean_text(element.text) if element else ""

    def process_value(self, key, value):
        """
        抽出した値を処理ルールに基づいて処理

        Args:
            key: 処理対象のキー
            value: 処理対象の値

        Returns:
            処理後の値
        """
        if not value:
            return ""

        if key not in self.processor_rules:
            return value

        rule = self.processor_rules[key]

        if rule == "currency":
            return process_currency(value)
        elif rule == "number":
            return extract_number_from_text(value)
        elif rule == "age":
            return process_age(value)
        else:
            return value

    def parse(self):
        """
        ページ全体を解析して物件情報を抽出する抽象メソッド
        サブクラスでオーバーライドする必要がある

        Returns:
            物件情報の辞書
        """
        raise NotImplementedError("Subclasses must implement parse() method")


class FavoritePatternParser(BaseParser):
    """
    お気に入りパターン用のパーサー
    """

    def __init__(self, soup, url):
        super().__init__("favorite", soup, url)

    def parse(self):
        """
        ページ全体を解析して物件情報を抽出

        Returns:
            物件情報の辞書
        """
        # 物件ID（URLの末尾から抽出）
        property_id = self.url.split("_")[-1].split("/")[0]

        # 物件名
        property_name = self.get_text("property_name")

        # 基本情報
        rent = self.process_value("rent", self.get_text("rent"))
        management_fee = self.process_value(
            "management_fee", self.get_text("management_fee")
        )
        deposit = self.process_value("deposit", self.get_text("deposit"))
        key_money = self.process_value("key_money", self.get_text("key_money"))

        # 物件詳細
        layout = self.get_text("layout")
        area = self.process_value("area", self.get_text("area"))
        direction = self.get_text("direction")
        building_type = self.get_text("building_type")
        age = self.process_value("age", self.get_text("age"))

        # 住所・アクセス
        address = self.get_text("address")
        access_list = self.get_text("access")
        access = (
            " / ".join(access_list) if isinstance(access_list, list) else access_list
        )

        # 入居情報
        move_in = self.get_text("move_in")

        # 詳細情報（追加項目）
        layout_detail = self.get_text("layout_detail")
        structure = self.get_text("structure")
        floor = self.get_text("floor")
        conditions = self.get_text("conditions")

        # 周辺情報
        surrounding_list = self.get_text("surrounding")
        surrounding = (
            " / ".join(surrounding_list)
            if isinstance(surrounding_list, list)
            else surrounding_list
        )

        # 情報更新日
        update_date = self.get_text("update_date")

        # 現在時刻（スクレイピング実行時刻）
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 結果を辞書として返す
        result = {
            "property_id": property_id,
            "name": property_name,
            "address": address,
            "access": access,
            "rent": rent,
            "management_fee": management_fee,
            "deposit": deposit,
            "key_money": key_money,
            "layout": layout,
            "area": area,
            "direction": direction,
            "building_type": building_type,
            "age": age,
            "layout_detail": layout_detail,
            "structure": structure,
            "floor": floor,
            "move_in": move_in,
            "conditions": conditions,
            "surrounding": surrounding,
            "update_date": update_date,
            "update_time": update_time,
        }

        return result
