# SUUMO 物件情報取得ツール

SUUMO の物件情報を自動的にスクレイピングして Google Spreadsheet に保存するツールです。

## 機能

- 新規物件のみ追加モード
- 全物件情報更新モード
- 単一 URL 処理モード
- デバッグモード

## 新しいプロジェクト構成

```
suumo-scraper/
│
├── src/
│   └── suumo_scraper/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── scraper/
│       │   ├── __init__.py
│       │   ├── core.py
│       │   ├── pattern_parsers.py
│       │   ├── patterns.json
│       │   ├── debug.py
│       │   └── parser_factory.py
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── text_processor.py
│       │   └── logger.py
│       └── sheets/
│           ├── __init__.py
│           ├── update.py
│           └── connection.py
│
├── tests/
│   └── __init__.py
│
├── data/
│
├── Pipfile
├── setup.py
├── Dockerfile
├── README.md
└── .gitignore
```

## セットアップ

1. Pipenv のインストール

```bash
pip install pipenv
```

2. 依存関係のインストール

```bash
pipenv install
```

3. 開発用依存関係のインストール

```bash
pipenv install --dev
```

## 使い方

```bash
# Pipenvを使用
pipenv run start --mode new_only
pipenv run start --mode full_update
pipenv run start --url [URL]
pipenv run start --debug

# または直接Pythonモジュールを実行
python -m src.suumo_scraper.main --mode new_only
python -m src.suumo_scraper.main --mode full_update
python -m src.suumo_scraper.main --url [URL]
python -m src.suumo_scraper.main --debug
```

## Google Cloud Run での実行

このプロジェクトは Google Cloud Run でのデプロイに対応しています。デプロイには以下のコマンドを使用します：

```bash
gcloud run deploy suumo-scraper \
  --source . \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

## 開発

開発時は以下のコマンドが利用できます：

```bash
# テスト実行
pipenv run test

# コードフォーマット
pipenv run black src tests

# リント
pipenv run flake8 src tests
```
