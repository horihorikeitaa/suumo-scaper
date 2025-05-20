#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SUUMOスクレイパーの動作確認用スクリプト
新規登録と更新処理の動作確認を行います
"""

import argparse
import json
import logging
import os
from datetime import datetime

# 内部モジュールのインポート
from src.suumo_scraper import config
from src.suumo_scraper.utils.logger import setup_logger
from src.suumo_scraper.scraper.core import scrape_suumo_property_info

# デバッグ用設定の上書き
config.SAVE_DEBUG_HTML = True
config.MAX_DEBUG_FILES = 5

# ロガーの設定
logger = setup_logger()
logger.setLevel(logging.DEBUG)


def test_scrape_url(url):
    """
    指定されたURLの物件情報をスクレイピングしてJSON形式で表示

    Args:
        url: スクレイピング対象のURL
    """
    logger.info(f"テスト: 物件情報のスクレイピング - {url}")
    try:
        # 物件情報を取得
        property_info = scrape_suumo_property_info(url)

        # 結果を表示
        print("\n=== スクレイピング結果 ===")
        print(json.dumps(property_info, indent=2, ensure_ascii=False))

        # 取得した情報を保存
        save_result(property_info)

        return property_info
    except Exception as e:
        logger.error(f"スクレイピングエラー: {e}")
        return {"error": str(e)}


def save_result(property_info):
    """
    スクレイピング結果をJSONファイルに保存

    Args:
        property_info: 物件情報
    """
    # 保存先ディレクトリの作成
    os.makedirs("test_results", exist_ok=True)

    # ファイル名の生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    property_id = property_info.get("property_id", "unknown")
    filename = f"test_results/property_{property_id}_{timestamp}.json"

    # JSON形式で保存
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(property_info, f, indent=2, ensure_ascii=False)

    logger.info(f"結果をファイルに保存しました: {filename}")


def test_batch_scrape(urls):
    """
    複数のURLを一括でスクレイピングして結果を表示

    Args:
        urls: スクレイピング対象のURLリスト
    """
    logger.info(f"テスト: 複数物件の一括スクレイピング - {len(urls)}件")

    results = []
    for i, url in enumerate(urls):
        logger.info(f"URLスクレイピング {i+1}/{len(urls)}: {url}")
        property_info = scrape_suumo_property_info(url)
        results.append(property_info)

    # 一括結果を表示
    print("\n=== 一括スクレイピング結果 ===")
    for i, result in enumerate(results):
        print(
            f"\n[{i+1}] {result.get('name', '名称不明')} - {result.get('property_id', '不明')}"
        )
        print(
            f"   家賃: {result.get('rent', '不明')}, 間取り: {result.get('layout', '不明')}"
        )

    # 一括結果をJSONファイルに保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results/batch_results_{timestamp}.json"
    os.makedirs("test_results", exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"一括結果をファイルに保存しました: {filename}")
    return results


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="SUUMOスクレイパー動作確認ツール")
    parser.add_argument("--url", type=str, help="単一のURLをスクレイピング")
    parser.add_argument(
        "--urls-file", type=str, help="URLリストを含むファイルパス（1行に1URL）"
    )
    parser.add_argument(
        "--sample", action="store_true", help="サンプルURLを使用してテスト"
    )

    args = parser.parse_args()

    # サンプルURLのリスト
    sample_urls = [
        "https://suumo.jp/chintai/bc_100437808558/",
        "https://suumo.jp/chintai/tokyo/sc_shinjuku/jnc_000068928596/?bc=100437528760",
        "https://suumo.jp/chintai/jnc_000054986064/?bc=100258748188",
    ]

    # URLの取得（単一URL、ファイル、またはサンプル）
    target_urls = []

    if args.url:
        target_urls = [args.url]
    elif args.urls_file:
        try:
            with open(args.urls_file, "r", encoding="utf-8") as f:
                target_urls = [url.strip() for url in f.readlines() if url.strip()]
                logger.info(f"URLファイルから{len(target_urls)}件のURLを読み込みました")
        except Exception as e:
            logger.error(f"URLファイルの読み込みエラー: {e}")
            return
    elif args.sample:
        target_urls = sample_urls
        logger.info(f"サンプルURL {len(sample_urls)}件 を使用します")
    else:
        # パラメータがない場合はサンプルの最初のURLを使用
        target_urls = [sample_urls[0]]
        logger.info(
            f"パラメータ指定がないため、サンプルURLを使用します: {target_urls[0]}"
        )

    # 処理の実行
    if len(target_urls) == 1:
        # 単一URLの場合は詳細情報を表示
        test_scrape_url(target_urls[0])
    else:
        # 複数URLの場合は一括処理
        test_batch_scrape(target_urls)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("ユーザーによる中断")
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
