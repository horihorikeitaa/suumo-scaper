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
        self.patterns = load_patterns()

        # パターン定義の読み込み
        if pattern_name not in self.patterns:
            raise ValueError(f"Unknown pattern: {pattern_name}")

        self.config = self.patterns[pattern_name]
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

    def __init__(self, soup, url, pattern_name="favorite_gallery"):
        super().__init__(pattern_name, soup, url)
        self.soup = soup
        self.url = url
        # 追加のパターンを読み込む
        self.additional_patterns = {}
        for pattern_name, pattern_config in self.patterns.items():
            if (
                pattern_name != self.pattern_name
                and "pattern_identifier" in pattern_config
            ):
                identifier = pattern_config["pattern_identifier"]
                if soup.select_one(identifier):
                    self.additional_patterns[pattern_name] = pattern_config

    def get_from_any_pattern(self, key):
        """
        すべてのパターンから指定されたキーの要素を検索して最初に見つかった値を返す

        Args:
            key: セレクタのキー

        Returns:
            要素のテキスト、見つからなかった場合は空文字列
        """
        # まず現在のパターンから検索
        value = self.get_text(key)
        if value:
            return value

        # 追加のパターンから検索
        for pattern_name, pattern_config in self.additional_patterns.items():
            selectors = pattern_config.get("selectors", {})
            if key in selectors:
                selector = selectors[key]
                selector_type = pattern_config.get("selector_types", {}).get(
                    key, "single"
                )

                if selector_type == "multiple":
                    elements = self.soup.select(selector)
                    if elements:
                        return [clean_text(el.text) for el in elements]
                else:
                    element = self.soup.select_one(selector)
                    if element:
                        return clean_text(element.text)

        return ""

    def process_from_any_pattern(self, key):
        """
        すべてのパターンから指定されたキーの値を取得して処理

        Args:
            key: 処理対象のキー

        Returns:
            処理後の値
        """
        value = self.get_from_any_pattern(key)

        # 値を処理
        # まず現在のパターンのルールを確認
        if key in self.processor_rules:
            return self.process_value(key, value)

        # 追加のパターンのルールを確認
        for pattern_name, pattern_config in self.additional_patterns.items():
            processor_rules = pattern_config.get("processor_rules", {})
            if key in processor_rules:
                rule = processor_rules[key]
                if rule == "currency":
                    return process_currency(value)
                elif rule == "number":
                    return extract_number_from_text(value)
                elif rule == "age":
                    return process_age(value)

        return value

    def parse(self):
        """
        ページ全体を解析して物件情報を抽出

        Returns:
            物件情報の辞書
        """
        # 物件ID（URLの末尾から抽出）
        property_id = self.url.split("_")[-1].split("/")[0]

        # ページから物件名を取得（h1タグからの直接取得も試みる）
        property_name = self.get_from_any_pattern("property_name")
        if not property_name:
            h1_tag = self.soup.select_one("h1.section_h1-header-title")
            if h1_tag:
                property_name = clean_text(h1_tag.text)

        # 結果を辞書として返す
        result = {
            "property_id": property_id,
            "name": property_name,
            "address": self.get_from_any_pattern("address"),
            "access": self.get_from_any_pattern("access"),
            "rent": self.process_from_any_pattern("rent"),
            "management_fee": self.process_from_any_pattern("management_fee"),
            "deposit": self.process_from_any_pattern("deposit"),
            "key_money": self.process_from_any_pattern("key_money"),
            "layout": self.get_from_any_pattern("layout"),
            "area": self.process_from_any_pattern("area"),
            "direction": self.get_from_any_pattern("direction"),
            "building_type": self.get_from_any_pattern("building_type"),
            "age": self.process_from_any_pattern("age"),
            "layout_detail": self.get_from_any_pattern("layout_detail"),
            "structure": self.get_from_any_pattern("structure"),
            "floor": self.get_from_any_pattern("floor"),
            "move_in": self.get_from_any_pattern("move_in"),
            "conditions": self.get_from_any_pattern("conditions"),
            "surrounding": self.get_from_any_pattern("surrounding"),
            "update_date": self.get_from_any_pattern("update_date"),
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # リスト型の値を文字列に変換
        for key, value in result.items():
            if isinstance(value, list):
                result[key] = " / ".join(value)

        return result
