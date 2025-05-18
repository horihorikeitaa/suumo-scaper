import requests
from bs4 import BeautifulSoup
import logging
import os
import json
from datetime import datetime
import config
from scraper.core import save_html_for_debug
from scraper.parser_factory import create_parser, detect_pattern, patterns


def debug_scrape_url(url: str, save_html: bool = True):
    """
    指定されたURLの物件情報をデバッグ用に詳細な情報とともに取得する

    Args:
        url: スクレイピング対象のURL
        save_html: HTMLを保存するかどうか

    Returns:
        デバッグ情報を含む辞書
    """
    print(f"URLのデバッグ解析を開始: {url}")

    try:
        # HTMLを取得
        print("HTMLを取得中...")
        html_content = None
        html_file = None

        # ローカルファイルかURLかを判断
        if url.startswith("file://"):
            local_path = url.replace("file://", "")
            try:
                with open(local_path, "rb") as f:
                    html_content = f.read()
                print(f"ローカルファイルから読み込み: {local_path}")
            except Exception as e:
                print(f"ローカルファイルの読み込みに失敗: {e}")
                raise
        else:
            # 通常のURLの場合
            r = requests.get(
                url,
                timeout=config.REQUEST_TIMEOUT,
                headers={"User-Agent": config.USER_AGENT},
            )
            r.raise_for_status()
            html_content = r.content

        # HTMLを保存
        if save_html and not url.startswith("file://"):
            html_file = save_html_for_debug(url, html_content)
            print(f"HTML保存完了: {html_file}")

        # BeautifulSoupでパース
        print("HTMLを解析中...")
        soup = BeautifulSoup(html_content, "html.parser")

        # デバッグ情報の収集
        debug_info = {
            "url": url,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "page_title": soup.title.text if soup.title else "タイトルなし",
            "patterns": {},
            "selectors": {},
            "raw_data": {},
            "processed_data": {},
            "html_file": html_file,
        }

        # パターン判別
        detected_pattern = detect_pattern(soup)
        debug_info["detected_pattern"] = detected_pattern

        # 各パターンの検出を確認
        for pattern_name, pattern_config in patterns.items():
            pattern_identifier = pattern_config.get("pattern_identifier")
            if pattern_identifier:
                is_detected = bool(soup.select_one(pattern_identifier))
                debug_info["patterns"][pattern_name] = {
                    "detected": is_detected,
                    "identifier": pattern_identifier,
                }

        # 検出されたパターンのセレクタ情報を詳細に調査
        if detected_pattern:
            pattern_config = patterns[detected_pattern]
            selectors = pattern_config.get("selectors", {})

            # 各セレクタの動作を確認
            for key, selector in selectors.items():
                selector_type = pattern_config.get("selector_types", {}).get(
                    key, "single"
                )
                if selector_type == "multiple":
                    elements = soup.select(selector)
                    debug_info["selectors"][key] = {
                        "selector": selector,
                        "type": selector_type,
                        "found": len(elements) > 0,
                        "count": len(elements),
                    }
                    if len(elements) > 0:
                        debug_info["raw_data"][key] = [
                            el.text.strip() for el in elements[:5]
                        ]  # 最初の5つだけ表示
                else:
                    element = soup.select_one(selector)
                    debug_info["selectors"][key] = {
                        "selector": selector,
                        "type": selector_type,
                        "found": element is not None,
                    }
                    if element:
                        debug_info["raw_data"][key] = element.text.strip()

        # パーサーで処理してみる
        try:
            parser = create_parser(soup, url)
            property_info = parser.parse()
            debug_info["processed_data"] = property_info
            debug_info["parse_success"] = True
        except Exception as e:
            debug_info["parse_success"] = False
            debug_info["parse_error"] = str(e)

        return debug_info

    except Exception as e:
        print(f"デバッグ解析中にエラーが発生: {e}")
        return {
            "url": url,
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
