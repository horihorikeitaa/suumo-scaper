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