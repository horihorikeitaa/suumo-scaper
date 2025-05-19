# Google Cloud Run へのデプロイ手順

このドキュメントでは、SUUMO Scrapper アプリケーションを Google Cloud Run にデプロイするための詳細な手順を説明します。

## 目次

- [準備作業](#準備作業)
- [認証情報の管理](#認証情報の管理)
- [アプリケーションの設定](#アプリケーションの設定)
- [コンテナのビルドとデプロイ](#コンテナのビルドとデプロイ)
- [Google Apps Script との連携](#google-apps-scriptとの連携)
- [トラブルシューティング](#トラブルシューティング)

## 準備作業

### 1. Google Cloud SDK のインストール

MacOS の場合:

```bash
brew install --cask google-cloud-sdk
```

インストール確認:

```bash
gcloud --version
```

### 2. Google Cloud へのログイン

```bash
gcloud auth login
```

### 3. プロジェクト ID の確認と設定

プロジェクト一覧を表示:

```bash
gcloud projects list
```

プロジェクトの設定:

```bash
# プロジェクトIDを設定
gcloud config set project suumo-scraper-460206
```

### 4. 必要な API の有効化

```bash
# 必要なAPIを有効化
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
```

## 認証情報の管理

Google Sheets にアクセスするための認証情報を安全に管理します。

### 1. Secret Manager での認証情報の管理

```bash
# Secret Managerにシークレットを作成
gcloud secrets create suumo-scraper-credentials \
  --replication-policy="automatic"

# 認証情報JSONファイルの内容をシークレットの新しいバージョンとして追加
gcloud secrets versions add suumo-scraper-credentials \
  --data-file="suumo-scraper-460206-6734b711c3fa.json"
```

### 2. サービスアカウントの作成と権限設定

```bash
# サービスアカウントを作成
gcloud iam service-accounts create suumo-scraper-sa \
  --display-name="SUUMO Scraper Service Account"

# プロジェクトIDを変数に設定
PROJECT_ID="suumo-scraper-460206"

# サービスアカウントに必要な権限を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:suumo-scraper-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# シークレットへのアクセス権を付与
gcloud secrets add-iam-policy-binding suumo-scraper-credentials \
  --member="serviceAccount:suumo-scraper-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## アプリケーションの設定

### 1. Cloud Functions 用のエントリーポイントの作成

`src/suumo_scraper/cloud_function.py` ファイルを作成し、以下の内容を追加:

```python
import json
import functions_framework
from flask import jsonify
from src.suumo_scraper.main import update_suumo_sheet
from src.suumo_scraper import config

@functions_framework.http
def suumo_scraper(request):
    """
    Google Cloud Functionsのエントリーポイント
    HTTPリクエストを受け取り、SUUMOスクレイピングを実行する
    GASからリクエストが送信されることを想定
    """
    # CORSヘッダーを設定
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600'
    }

    # OPTIONSリクエスト（プリフライトリクエスト）への対応
    if request.method == 'OPTIONS':
        return ('', 204, headers)

    # POSTリクエスト以外は拒否
    if request.method != 'POST':
        return (jsonify({'error': 'Method not allowed'}), 405, headers)

    try:
        # リクエストのJSONデータを取得
        request_json = request.get_json(silent=True)

        if not request_json:
            return (jsonify({'error': 'No JSON data provided'}), 400, headers)

        # パラメータの取得
        mode = request_json.get('mode', config.MODE_NEW_ONLY)
        url = request_json.get('url', None)

        # モードのバリデーション
        if mode not in [config.MODE_NEW_ONLY, config.MODE_FULL_UPDATE]:
            return (jsonify({'error': f'Invalid mode: {mode}'}), 400, headers)

        # スクレイピング実行
        result = update_suumo_sheet(update_mode=mode, new_url=url)

        # 結果を返す
        return (jsonify(result), 200, headers)

    except Exception as e:
        # エラーハンドリング
        error_response = {
            'status': 'error',
            'error_message': str(e)
        }
        return (jsonify(error_response), 500, headers)
```

### 2. 認証情報の取得部分の修正

`src/suumo_scraper/sheets/connection.py` ファイルの `setup_sheet_connection` 関数を修正:

```python
def setup_sheet_connection():
    """
    Google Spreadsheetsに接続するための関数
    ローカルファイルまたは環境変数から認証情報を取得
    """
    try:
        # 環境変数から認証情報を取得する方法を追加
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
            # 環境変数からJSON文字列を取得してJSONオブジェクトに変換
            creds_json = json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALS_JSON'])
            creds = Credentials.from_service_account_info(creds_json, scopes=config.SCOPES)
            logging.info("環境変数から認証情報を取得しました")
        elif os.path.exists(config.CREDS_FILE_PATH):
            # ローカルファイルから認証情報を取得
            creds = Credentials.from_service_account_file(
                config.CREDS_FILE_PATH, scopes=config.SCOPES
            )
            logging.info(f"ファイルから認証情報を取得しました: {config.CREDS_FILE_PATH}")
        else:
            # デフォルトの認証情報（Cloud Run上で使用するアプリケーションデフォルト認証情報）
            try:
                # このパスはCloud Runでマウントされた認証情報
                creds = Credentials.from_service_account_file(
                    "/secrets/credentials.json", scopes=config.SCOPES
                )
                logging.info("Cloud Runのマウントされた認証情報を使用します")
            except FileNotFoundError:
                # アプリケーションデフォルト認証情報を試す
                import google.auth
                creds, _ = google.auth.default(scopes=config.SCOPES)
                logging.info("アプリケーションデフォルト認証情報を使用します")
```

### 3. Dockerfile の作成

プロジェクトルートに以下の内容で `Dockerfile` を作成:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# アプリケーションコードとセットアップをコピー
COPY src/ ./src/
COPY setup.py ./

# setup.pyから依存関係をインストール
RUN pip install --no-cache-dir -e .

# functions-frameworkを明示的にインストール
RUN pip install --no-cache-dir functions-framework

# 環境変数の設定
ENV PYTHONPATH=/app
ENV PORT=8080

# Cloud Functionsのエントリーポイントを指定
CMD exec functions-framework --target=suumo_scraper --source=src/suumo_scraper/cloud_function.py --port=$PORT
```

### 4. .dockerignore ファイルの作成

認証情報などをコンテナに含めないよう、`.dockerignore` ファイルを作成:

```
# 認証情報ファイルを除外
*.json
!package.json
!patterns.json

# Git関連
.git/
.gitignore

# Python関連
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
.installed.cfg
*.egg

# テスト関連
tests/
.pytest_cache/

# VSCode設定
.vscode/

# データディレクトリ
data/

# その他
*.log
*.bak
.DS_Store
```

## コンテナのビルドとデプロイ

### 1. コンテナのビルド

```bash
# プロジェクトIDを変数に設定
PROJECT_ID="suumo-scraper-460206"

# コンテナをビルド
gcloud builds submit --tag gcr.io/$PROJECT_ID/suumo-scraper
```

### 2. Cloud Run へのデプロイ

```bash
# Cloud Runにデプロイ
gcloud run deploy suumo-scraper \
  --image gcr.io/$PROJECT_ID/suumo-scraper \
  --platform managed \
  --region asia-northeast1 \
  --service-account="suumo-scraper-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --allow-unauthenticated \
  --set-secrets="/secrets/credentials.json=suumo-scraper-credentials:latest"
```

デプロイ完了後、サービス URL が表示されます。この URL を控えておいてください。

### 3. デプロイの確認

```bash
# デプロイされたサービスの確認
gcloud run services list

# デプロイされたサービスの詳細を確認
gcloud run services describe suumo-scraper
```

## Google Apps Script との連携

Google Apps スクリプトから、Cloud Run 上のアプリケーションを呼び出します。

### GAS スクリプトの例

```javascript
function callSuumoScraper(mode) {
  // Cloud RunのURL（デプロイ時に表示されたURL）
  const url = "https://suumo-scraper-xxx-an.a.run.app"; // ← 実際のURLに置き換える

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

## トラブルシューティング

### サービスアカウントが存在しないエラー

エラーメッセージ:

```
ERROR: Service account XXX does not exist.
```

対応策:

1. サービスアカウントを作成
2. 必要な権限を付与

### Pipenv でのインストールエラー

エラーメッセージ:

```
ERROR:: --system is intended to be used for Pipfile installation, not installation of specific packages. Aborting.
```

対応策:

1. Dockerfile を修正し、setup.py を使用して依存関係をインストール
2. または、pipenv コマンドを修正

### 認証情報に関するエラー

対応策:

1. Secret Manager に認証情報が正しく保存されているか確認
2. サービスアカウントに適切な権限が与えられているか確認
3. マウントパスが正しいか確認
