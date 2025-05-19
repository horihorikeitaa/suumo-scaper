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
        検出されたパターン名のリスト、見つからなかった場合は空リスト
    """
    logging.debug("HTMLパターンの判別を開始")

    detected_patterns = []
    # 各パターンの識別子を確認
    for pattern_name, pattern_config in patterns.items():
        pattern_identifier = pattern_config.get("pattern_identifier")
        if pattern_identifier and soup.select_one(pattern_identifier):
            logging.debug(f"パターン '{pattern_name}' を検出")
            detected_patterns.append(pattern_name)

    if not detected_patterns:
        logging.warning("既知のパターンが検出できませんでした")

    return detected_patterns


def create_parser(soup, url):
    """
    適切なパーサーを作成する

    Args:
        soup: BeautifulSoupオブジェクト
        url: スクレイピング対象のURL

    Returns:
        パーサーオブジェクト
    """
    detected_patterns = detect_pattern(soup)

    if not detected_patterns:
        logging.warning(
            f"未知のパターンのため、お気に入りパターンで解析を試みます: {url}"
        )
        return FavoritePatternParser(soup, url, "favorite_gallery")

    # 複数のパターンが検出された場合、favorite_galleryを優先
    if "favorite_gallery" in detected_patterns:
        return FavoritePatternParser(soup, url, "favorite_gallery")
    elif "favorite_contents" in detected_patterns:
        return FavoritePatternParser(soup, url, "favorite_contents")
    else:
        # その他のパターンが検出された場合（将来的な拡張用）
        return FavoritePatternParser(soup, url, detected_patterns[0])
