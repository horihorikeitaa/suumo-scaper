# SUUMO Scraper の使い方

このドキュメントでは、SUUMO Scraper アプリケーションの使い方について説明します。

## 目次

- [概要](#概要)
- [Google Spreadsheets 連携](#google-spreadsheets連携)
- [利用可能な機能](#利用可能な機能)
- [Google Apps Script 設定](#google-apps-script設定)
- [実行と結果確認](#実行と結果確認)

## 概要

SUUMO Scraper は、SUUMO ウェブサイトから不動産情報をスクレイピングし、Google Spreadsheet に保存するツールです。
Google Cloud Run 上でホストされ、Google Apps Script（GAS）から HTTP リクエストで実行できます。

## Google Spreadsheets 連携

### スプレッドシートの準備

1. 新しい Google Spreadsheet を作成するか、既存のシートを使用します
2. 以下のシートを作成します：
   - `物件情報` シート：スクレイピングした物件情報を保存するメインシート
   - `main` シート：新規 URL を入力する管理用シート

### 物件情報シートの構成

物件情報シートには以下のカラムを設定します：

1. #（通し番号）
2. URL
3. 物件 ID
4. 物件名
5. 住所
6. アクセス
7. 家賃
8. 管理費・共益費
9. 敷金
10. 礼金
11. 間取り
12. 専有面積
13. 向き
14. 建物種別
15. 築年数
16. 間取り詳細
17. 構造
18. 階数
19. 入居
20. 条件
21. 周辺情報
22. 情報更新日
23. 更新日時

### main シートの構成

main シートには B9:B18 の範囲に新規追加したい SUUMO 物件の URL を入力できるようにします。

## 利用可能な機能

SUUMO Scraper では以下の機能が利用できます：

### 1. 新規物件の追加

main シートに入力された URL の物件情報を取得し、物件情報シートに新規追加します。
既に登録済みの URL は無視されます。

### 2. 全物件情報の更新

物件情報シートに登録されている全物件の情報を最新の状態に更新します。
URL ごとに再スクレイピングを行い、最新情報に更新します。

## Google Apps Script 設定

### 1. スプレッドシートにスクリプトを追加

1. スプレッドシートの「拡張機能」→「Apps Script」を選択
2. 以下のコードを新しいスクリプトファイルに追加します：

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

### 2. ボタンの追加

1. スプレッドシートに「新規追加」「全更新」ボタンを追加します：
   - 「挿入」→「描画」を選択
   - ボタンを描画
   - ボタンを右クリックして「スクリプトを割り当て」を選択
   - 「新規追加」ボタンには`addNewProperties`関数を割り当て
   - 「全更新」ボタンには`updateAllProperties`関数を割り当て

## 実行と結果確認

### 新規物件の追加手順

1. main シートの B9:B18 範囲に新規 URL を入力
2. 「新規追加」ボタンをクリック
3. 処理が完了するまで待機（数十秒〜数分）
4. 物件情報シートに新しい行が追加されていることを確認

### 全物件更新手順

1. 「全更新」ボタンをクリック
2. 処理が完了するまで待機（物件数によっては数分かかる場合あり）
3. 物件情報シートの内容が更新されていることを確認

### 注意事項

- 処理時間はスクレイピングする物件数によって変動します
- 同時に多数の URL を処理すると、SUUMO サイトへの負荷が高まる可能性があります
- 大量の物件を一度に更新する場合は、処理時間が長くなり、タイムアウトする可能性があります
