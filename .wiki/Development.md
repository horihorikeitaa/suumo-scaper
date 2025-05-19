# 開発ガイド

このドキュメントは、SUUMO Scraper の開発者向けガイドです。プロジェクトの構造、開発環境のセットアップ方法、コードの拡張方法について説明します。

## 目次

- [プロジェクト構成](#プロジェクト構成)
- [開発環境のセットアップ](#開発環境のセットアップ)
- [主要コンポーネント](#主要コンポーネント)
- [コードの拡張方法](#コードの拡張方法)
- [テスト](#テスト)
- [デバッグ方法](#デバッグ方法)

## プロジェクト構成

プロジェクトは以下のディレクトリ構造になっています：

```
suumo-scraper/
│
├── src/
│   └── suumo_scraper/
│       ├── __init__.py
│       ├── main.py              # メインアプリケーションロジック
│       ├── config.py            # 設定ファイル
│       ├── cloud_function.py    # Cloud Run/Functions用エントリーポイント
│       ├── scraper/             # スクレイピング関連
│       │   ├── __init__.py
│       │   ├── core.py          # スクレイピングコア機能
│       │   ├── pattern_parsers.py # パースロジック
│       │   ├── patterns.json    # パターン定義
│       │   ├── debug.py         # デバッグ用
│       │   └── parser_factory.py # パーサー生成
│       ├── utils/               # ユーティリティ
│       │   ├── __init__.py
│       │   ├── text_processor.py # テキスト処理
│       │   └── logger.py        # ロギング
│       └── sheets/              # スプレッドシート操作
│           ├── __init__.py
│           ├── update.py        # データ更新
│           └── connection.py    # シート接続
│
├── tests/                       # テスト
│
├── data/                        # データ
│
├── Pipfile                      # 依存関係
├── Pipfile.lock                 # 固定依存関係
├── setup.py                     # セットアップ
├── Dockerfile                   # Dockerコンテナ定義
├── .dockerignore                # Dockerビルド除外設定
├── README.md                    # プロジェクト説明
└── .gitignore                   # Gitの除外設定
```

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/[your-username]/suumo-scraper.git
cd suumo-scraper
```

### 2. 依存関係のインストール

```bash
# Pipenvのインストール
pip install pipenv

# 依存関係のインストール
pipenv install

# 開発用依存関係のインストール
pipenv install --dev
```

### 3. 開発環境の設定

Google API 認証情報を取得して配置します：

1. [Google Cloud Console](https://console.cloud.google.com/)からサービスアカウントキーを取得
2. JSON ファイルをプロジェクトのルートディレクトリに保存
3. `config.py`の`CREDS_FILE_PATH`を設定

## 主要コンポーネント

### 1. スクレイピングコンポーネント

スクレイピング処理は`scraper`パッケージで行われます。

- `core.py`: メインのスクレイピング処理
- `pattern_parsers.py`: HTML 解析ロジック
- `patterns.json`: SUUMO サイトの HTML パターン定義

### 2. スプレッドシート連携

スプレッドシート操作は`sheets`パッケージで行われます。

- `connection.py`: Google Sheets API との接続
- `update.py`: データの更新処理（追加/更新）

### 3. クラウドデプロイ

- `cloud_function.py`: Cloud Functions のエントリーポイント
- `Dockerfile`: コンテナ定義

## コードの拡張方法

### 新しいスクレイピングパターンの追加

SUUMO サイトのレイアウトが変更された場合、以下のファイルを更新します：

1. `patterns.json`にセレクタパターンを追加
2. 必要に応じて`pattern_parsers.py`にパース処理を追加

```python
# pattern_parsers.py
def parse_new_pattern(soup, selector):
    # 新しいパターンの解析処理
    element = soup.select_one(selector)
    if element:
        return element.text.strip()
    return None
```

### 新しい API エンドポイントの追加

追加の API エンドポイントが必要な場合、`cloud_function.py`を修正します：

```python
@functions_framework.http
def suumo_scraper(request):
    # 既存の処理...

    # 新しいエンドポイントのパラメータを追加
    action = request_json.get('action', 'default')

    if action == 'new_action':
        # 新しい処理を実装
        result = some_new_function()
        return (jsonify(result), 200, headers)

    # 既存の処理...
```

## テスト

### テストの実行

```bash
# 全テストを実行
pipenv run pytest

# 特定のテストを実行
pipenv run pytest tests/test_scraper.py
```

### 新しいテストの追加

テストは`tests`ディレクトリに追加します：

```python
# tests/test_new_feature.py
def test_new_feature():
    # テストコード
    result = my_new_function()
    assert result == expected_value
```

## デバッグ方法

### ローカルでのデバッグ実行

```bash
# デバッグモードで実行
pipenv run python -m src.suumo_scraper.main --debug

# 単一URL処理で実行
pipenv run python -m src.suumo_scraper.main --url [URL]
```

### Cloud Run ローカルエミュレーション

Cloud Run をローカルで実行してデバッグする方法：

```bash
# functions-frameworkを使用して実行
pipenv run functions-framework --target=suumo_scraper --source=src/suumo_scraper/cloud_function.py --debug
```

リクエストの送信：

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"mode":"new_only"}' \
  http://localhost:8080
```

### ログの確認

Cloud Run デプロイ後のログ確認：

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=suumo-scraper" --limit=50
```
