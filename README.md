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
│       ├── cloud_function.py  # Cloud Run用のエントリーポイント
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

## Google Cloud Run でのデプロイと実行

このプロジェクトは Google Cloud Run でのデプロイに対応しています。

### 事前準備

1. Google Cloud SDK がインストールされていることを確認
2. プロジェクトの設定

```bash
gcloud config set project [YOUR_PROJECT_ID]
```

### 認証情報の管理

Cloud Run 環境では、Google 認証情報を以下のいずれかの方法で管理できます：

#### 1. シークレットマネージャーを使用する方法（推奨）

```bash
# シークレットマネージャーに認証ファイルを登録
gcloud secrets create suumo-scraper-credentials --data-file="suumo-scraper-460206-6734b711c3fa.json"

# シークレットをCloud Runからアクセスできるように権限を付与
gcloud secrets add-iam-policy-binding suumo-scraper-credentials \
    --member="serviceAccount:[YOUR_SERVICE_ACCOUNT]@[YOUR_PROJECT_ID].iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

#### 2. 環境変数として設定する方法

```bash
# 認証ファイルのJSON内容を環境変数として設定
export CREDS_JSON=$(cat suumo-scraper-460206-6734b711c3fa.json | jq -c)
```

### ビルドとデプロイ

```bash
# コンテナをビルドしてContainer Registryにプッシュ
gcloud builds submit --tag gcr.io/[YOUR_PROJECT_ID]/suumo-scraper

# Cloud Runサービスをデプロイ（シークレットマネージャーを使用する場合）
gcloud run deploy suumo-scraper \
  --image gcr.io/[YOUR_PROJECT_ID]/suumo-scraper \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-secrets="GOOGLE_APPLICATION_CREDENTIALS=/secrets/credentials.json:suumo-scraper-credentials:latest"

# 環境変数を使用する場合
gcloud run deploy suumo-scraper \
  --image gcr.io/[YOUR_PROJECT_ID]/suumo-scraper \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_APPLICATION_CREDENTIALS_JSON=$CREDS_JSON"
```

### Google Apps Script からの呼び出し

Cloud Run デプロイ後、GAS から以下のように HTTP リクエストを送信できます：

```javascript
function callSuumoScraper(mode) {
  const url = "https://suumo-scraper-xxxxx-an.a.run.app"; // Cloud RunのURL

  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({
      mode: mode, // 'new_only' または 'full_update'
    }),
    muteHttpExceptions: true,
  };

  try {
    const response = UrlFetchApp.fetch(url, options);
    const result = JSON.parse(response.getContentText());
    return result;
  } catch (e) {
    console.error("エラーが発生しました: " + e.toString());
    return { status: "error", error_message: e.toString() };
  }
}

// 新規物件追加ボタン用の関数
function addNewProperties() {
  return callSuumoScraper("new_only");
}

// 全物件更新ボタン用の関数
function updateAllProperties() {
  return callSuumoScraper("full_update");
}
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
