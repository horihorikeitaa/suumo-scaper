#!/bin/bash

# Wikiリポジトリのクローンを一時的に作成
TEMP_DIR=$(mktemp -d)
echo "Cloning wiki repo to $TEMP_DIR..."

# Wikiリポジトリがまだ存在しない場合は初期化する
git ls-remote wiki &> /dev/null
if [ $? -ne 0 ]; then
  echo "Wiki repository doesn't exist yet. Creating initial empty repo..."
  cd $TEMP_DIR
  git init
  git remote add origin https://github.com/horihorikeitaa/suumo-scaper.wiki.git
  touch Home.md
  echo "# SUUMO Scraper Wiki" > Home.md
  git add Home.md
  git commit -m "Initial commit"
  git branch -M master
  git push -u origin master
  cd -
  echo "Created initial wiki repository."
else
  git clone https://github.com/horihorikeitaa/suumo-scaper.wiki.git $TEMP_DIR
fi

# .wikiディレクトリの内容をコピー
echo "Copying .wiki content to wiki repo..."
cp -R .wiki/* $TEMP_DIR/

# Wikiリポジトリへコミットとプッシュ
cd $TEMP_DIR
git add .
git commit -m "Update wiki content from .wiki directory"
git push origin master
cd -

# 一時ディレクトリを削除
rm -rf $TEMP_DIR

echo "Wiki content successfully pushed to wiki repository." 