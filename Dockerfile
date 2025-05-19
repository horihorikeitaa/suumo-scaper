FROM python:3.11-slim

WORKDIR /app

# ビルド依存関係のインストール
RUN pip install --no-cache-dir pipenv

# Pipfileをコピーして依存関係をインストール
COPY Pipfile Pipfile.lock* ./
RUN pipenv install --deploy --system

# アプリケーションコードをコピー
COPY src/ ./src/
COPY setup.py ./

# 証明書ファイルをコピー（必要な場合）
COPY *.json ./

# 環境変数の設定
ENV PYTHONPATH=/app

# アプリケーションを実行
CMD ["python", "-m", "src.suumo_scraper.main"] 