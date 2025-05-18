import logging
from bs4 import BeautifulSoup
import json
import os
from scraper.pattern_parsers import BaseParser, FavoritePatternParser, load_patterns

# パターン定義の読み込み
patterns = load_patterns()


def detect_pattern(soup):
    """
    HTMLのパターンを判別する

    Args:
        soup: BeautifulSoupオブジェクト

    Returns:
        検出されたパターン名、見つからなかった場合はNone
    """
    logging.debug("HTMLパターンの判別を開始")

    # 各パターンの識別子を確認
    for pattern_name, pattern_config in patterns.items():
        pattern_identifier = pattern_config.get("pattern_identifier")
        if pattern_identifier and soup.select_one(pattern_identifier):
            logging.debug(f"パターン '{pattern_name}' を検出")
            return pattern_name

    logging.warning("既知のパターンが検出できませんでした")
    return None


def create_parser(soup, url):
    """
    適切なパーサーを作成する

    Args:
        soup: BeautifulSoupオブジェクト
        url: スクレイピング対象のURL

    Returns:
        パーサーオブジェクト
    """
    pattern = detect_pattern(soup)

    if pattern == "favorite":
        return FavoritePatternParser(soup, url)

    # パターンが検出できない場合はお気に入りパターンを試す
    logging.warning(f"未知のパターンのため、お気に入りパターンで解析を試みます: {url}")
    return FavoritePatternParser(soup, url)
