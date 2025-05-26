// 定数定義
const SHEET_NAMES = {
  PROPERTY: "物件情報",
  MASTER: "評価基準マスタ",
  HUSBAND: "物件採点_husband",
  WIFE: "物件採点_wife",
};

const PERSON = {
  HUSBAND: "husband",
  WIFE: "wife",
};

// 値の組み合わせ方法を定義（拡張可能）
const VALUE_COMBINATION_METHODS = {
  ADD: "add", // 加算
  MULTIPLY: "multiply", // 乗算
  AVERAGE: "average", // 平均
  MAX: "max", // 最大値
  MIN: "min", // 最小値
  CONCAT: "concat", // 文字列結合
};

// main処理（採点実行）
function main(mode = "all", targetNos = "") {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const propertySheet = ss.getSheetByName(SHEET_NAMES.PROPERTY);
  const wifeSheet = ss.getSheetByName(SHEET_NAMES.WIFE);
  const husbandSheet = ss.getSheetByName(SHEET_NAMES.HUSBAND);
  const masterSheet = ss.getSheetByName(SHEET_NAMES.MASTER);

  // 物件情報のヘッダーを取得（1行目）
  const propertyHeaders = propertySheet
    .getRange(1, 1, 1, propertySheet.getLastColumn())
    .getValues()[0];

  // 評価シートの共通ヘッダーとそれぞれの重みを取得
  const evaluationHeaders = getEvaluationHeaders(wifeSheet);
  const wifeWeights = getEvaluationWeights(wifeSheet, evaluationHeaders.length);
  const husbandWeights = getEvaluationWeights(
    husbandSheet,
    evaluationHeaders.length
  );

  // 対象物件と評価基準を取得
  const properties = getTargetProperties(propertySheet, mode, targetNos);
  const masterData = loadMasterData(masterSheet);

  // 各物件の採点処理
  for (let i = 0; i < properties.length; i++) {
    const row = properties[i];
    const rowIndex = row.rowIndex;
    const propertyValues = row.values;

    // 夫と妻の採点処理
    const wifeResult = calculateScores(
      masterData,
      evaluationHeaders,
      wifeWeights,
      propertyHeaders,
      propertyValues,
      PERSON.WIFE
    );

    const husbandResult = calculateScores(
      masterData,
      evaluationHeaders,
      husbandWeights,
      propertyHeaders,
      propertyValues,
      PERSON.HUSBAND
    );

    // 結果を反映
    updateScoreSheet(wifeSheet, rowIndex, wifeResult);
    updateScoreSheet(husbandSheet, rowIndex, husbandResult);
  }

  return {
    processedCount: properties.length,
    targetProperties: properties.length,
  };
}

// 評価シートのヘッダー取得（C列以降）
function getEvaluationHeaders(sheet) {
  return sheet.getRange(1, 3, 1, sheet.getLastColumn() - 2).getValues()[0];
}

// 評価シートの重み取得（2行目、C列以降）
function getEvaluationWeights(sheet, headerLength) {
  return sheet.getRange(2, 3, 1, headerLength).getValues()[0];
}

// スコア計算処理
function calculateScores(
  masterData,
  headers,
  weights,
  propertyHeaders,
  propertyValues,
  person
) {
  const rawScores = []; // 生のスコア（重み付け前）
  const weightedScores = []; // 重み付け後のスコア

  for (let j = 0; j < headers.length; j++) {
    const outputItem = headers[j];
    const weight = Number(weights[j]);

    // マスターから対応する入力項目とその値を特定
    const { inputItem, value } = findInputValueForOutputItem(
      masterData,
      outputItem,
      propertyHeaders,
      propertyValues,
      person
    );

    // スコア計算
    const score = getScoreFromMaster(masterData, outputItem, value, person);
    rawScores.push(score);
    weightedScores.push(score * weight);
  }

  // 総合点計算
  const totalScore = weightedScores.reduce((a, b) => a + b, 0);

  return {
    totalScore,
    rawScores,
    weightedScores,
  };
}

// 採点結果をシートに反映
function updateScoreSheet(sheet, rowIndex, result) {
  // 総合点を設定（B列）
  sheet.getRange(rowIndex + 2, 2).setValue(result.totalScore);

  // 各項目の重み付けされたスコアを設定（C列以降）
  sheet
    .getRange(rowIndex + 2, 3, 1, result.weightedScores.length)
    .setValues([result.weightedScores]);
}

// 出力項目に対応する入力項目と値を取得
function findInputValueForOutputItem(
  masterData,
  outputItem,
  propertyHeaders,
  propertyValues,
  person
) {
  // マスターデータから対応する入力項目を探す
  for (const item in masterData) {
    if (masterData[item][person] && item === outputItem) {
      // マスターの最初のルールから入力項目と組み合わせ方法を取得
      const rule = masterData[item][person][0];
      const inputItem = rule.inputItem;
      const combinationMethod = rule.combinationMethod;

      // 複数項目の値を取得・組み合わせ
      const value = getValueFromInputItems(
        inputItem,
        propertyHeaders,
        propertyValues,
        combinationMethod
      );

      return { inputItem, value };
    }
  }

  return { inputItem: null, value: null };
}

// 入力項目から値を取得・組み合わせ
function getValueFromInputItems(
  inputItem,
  propertyHeaders,
  propertyValues,
  combinationMethod = null
) {
  if (!inputItem) return null;

  // カンマ区切りかどうかをチェック
  if (inputItem.includes(",")) {
    const inputItems = inputItem.split(",").map((item) => item.trim());
    const values = [];

    // 各項目の値を取得
    for (const item of inputItems) {
      const value = getPropertyValue(item, propertyHeaders, propertyValues);
      if (value !== null) {
        values.push(value);
      }
    }

    // 組み合わせ方法が"-"の場合は組み合わせ処理をスキップ（最初の値を返す）
    if (combinationMethod === "-") {
      return values.length > 0 ? values[0] : null;
    }

    // 値の組み合わせ（マスタで指定された方法を使用）
    return combineValues(values, combinationMethod);
  } else {
    // 単一項目の場合
    return getPropertyValue(inputItem, propertyHeaders, propertyValues);
  }
}

// 物件情報から特定項目の値を取得（特殊処理含む）
function getPropertyValue(itemName, propertyHeaders, propertyValues) {
  const inputIndex = propertyHeaders.indexOf(itemName);
  if (inputIndex < 0) return null;

  const rawValue = propertyValues[inputIndex];

  // 特殊処理：アクセス項目から徒歩分数を抽出
  if (itemName === "アクセス") {
    return extractWalkingMinutes(rawValue);
  }

  // 数値に変換可能な場合は数値として扱う
  const numValue = Number(rawValue);
  return isNaN(numValue) ? rawValue : numValue;
}

// アクセス情報から徒歩分数を抽出（複数駅対応）
function extractWalkingMinutes(accessText) {
  if (!accessText) return null;

  // 複数の"歩XX分"パターンを検索して最小値を取得
  const walkMatches = String(accessText).match(/歩(\d+)分/g);
  if (walkMatches && walkMatches.length > 0) {
    const minutes = walkMatches.map((match) => {
      const num = match.match(/歩(\d+)分/);
      return num ? Number(num[1]) : Infinity;
    });
    return Math.min(...minutes);
  }

  return null;
}

// 値の組み合わせ処理（マスタ指定のみ）
function combineValues(values, combinationMethod = null) {
  if (values.length === 0) return null;
  if (values.length === 1) return values[0];

  // 組み合わせ方法が指定されていない場合はデフォルトで加算
  const method = combinationMethod || VALUE_COMBINATION_METHODS.ADD;

  switch (method) {
    case VALUE_COMBINATION_METHODS.ADD:
    case "add":
      return values.reduce((sum, val) => {
        const num = Number(val);
        return sum + (isNaN(num) ? 0 : num);
      }, 0);

    case VALUE_COMBINATION_METHODS.MULTIPLY:
    case "multiply":
      return values.reduce((product, val) => {
        const num = Number(val);
        return product * (isNaN(num) ? 1 : num);
      }, 1);

    case VALUE_COMBINATION_METHODS.AVERAGE:
    case "average":
      const numericValues = values
        .filter((val) => !isNaN(Number(val)))
        .map((val) => Number(val));
      return numericValues.length > 0
        ? numericValues.reduce((sum, val) => sum + val, 0) /
            numericValues.length
        : 0;

    case VALUE_COMBINATION_METHODS.MAX:
    case "max":
      const maxValues = values
        .filter((val) => !isNaN(Number(val)))
        .map((val) => Number(val));
      return maxValues.length > 0 ? Math.max(...maxValues) : 0;

    case VALUE_COMBINATION_METHODS.MIN:
    case "min":
      const minValues = values
        .filter((val) => !isNaN(Number(val)))
        .map((val) => Number(val));
      return minValues.length > 0 ? Math.min(...minValues) : 0;

    case VALUE_COMBINATION_METHODS.CONCAT:
    case "concat":
      return values.join("");

    default:
      // デフォルトは加算
      return values.reduce((sum, val) => {
        const num = Number(val);
        return sum + (isNaN(num) ? 0 : num);
      }, 0);
  }
}

// マスターデータ読み込み
function loadMasterData(sheet) {
  const data = sheet.getDataRange().getValues();
  const master = {};

  // ヘッダー行をスキップして2行目から処理
  for (let i = 1; i < data.length; i++) {
    // A列:出力項目, B列:物件情報の対象項目, C列:operator, D列:値, E列:スコア, F列:人物, G列:組み合わせ方法（オプション）
    const outputItem = data[i][0];
    const inputItem = data[i][1];
    const operator = data[i][2];
    const target = data[i][3];
    const score = data[i][4];
    const person = data[i][5];
    let combinationMethod = data[i][6] || null; // G列が空の場合はnull

    // 空行をスキップ
    if (!outputItem || !inputItem || !person) continue;

    // 組み合わせ方法の正規化
    if (combinationMethod) {
      combinationMethod = String(combinationMethod).trim();
      // 空文字列の場合はnullに変換
      if (combinationMethod === "" || combinationMethod === "-") {
        combinationMethod = null;
      }
    }

    if (!master[outputItem]) master[outputItem] = {};
    if (!master[outputItem][person]) master[outputItem][person] = [];

    master[outputItem][person].push({
      inputItem,
      operator,
      target,
      score,
      combinationMethod,
    });
  }

  return master;
}

// 対象物件取得
function getTargetProperties(sheet, mode, targetNos) {
  // 1行目がヘッダーなので2行目から取得
  const values = sheet
    .getRange(2, 1, Math.max(1, sheet.getLastRow() - 1), sheet.getLastColumn())
    .getValues();
  const results = [];

  if (mode === "all") {
    // 全物件を対象
    values.forEach((row, i) => {
      if (row[0]) {
        // 空行でなければ
        results.push({ rowIndex: i + 1, values: row });
      }
    });
  } else {
    // 指定された物件番号のみを対象
    let targetList = targetNos;

    // 文字列として渡された場合はカンマ区切りで配列に変換
    if (typeof targetNos === "string") {
      targetList = targetNos.split(",").map((n) => n.trim());
    }

    values.forEach((row, i) => {
      if (row[0] && targetList.includes(String(row[0]))) {
        results.push({ rowIndex: i + 1, values: row });
      }
    });
  }

  return results;
}

// 採点処理
function getScoreFromMaster(masterData, item, value, person) {
  if (!masterData[item] || !masterData[item][person]) return 0; // 該当ルールがない場合は0を返す

  const rules = masterData[item][person];

  for (const rule of rules) {
    if (matchValue(rule.operator, rule.target, value)) {
      return Number(rule.score);
    }
  }

  return 0; // マッチする条件がない場合は0を返す
}

// 条件マッチング処理
function matchValue(operator, target, actualValue) {
  // nullやundefinedの場合の処理
  if (actualValue === null || actualValue === undefined) {
    actualValue = "";
  }

  // operatorの正規化（CSVから読み込んだ場合の表記ゆれ対応）
  const normalizedOperator = String(operator).replace(/^'/, ""); // 先頭の'を除去

  switch (normalizedOperator) {
    case "=":
      return String(actualValue) == String(target);
    case "!=":
      return String(actualValue) != String(target);
    case ">":
      return Number(actualValue) > Number(target);
    case ">=":
      return Number(actualValue) >= Number(target);
    case "<":
      return Number(actualValue) < Number(target);
    case "<=":
      return Number(actualValue) <= Number(target);
    case "><": {
      const [min, max] = String(target)
        .split("-")
        .map((v) => Number(v.trim()));
      const val = Number(actualValue);
      return val >= min && val <= max;
    }
    case "in":
      // カンマ区切りの複数値に対応
      const targetValues = String(target)
        .split(",")
        .map((v) => v.trim());
      const actualStr = String(actualValue).trim();
      return targetValues.some((targetVal) => {
        // 完全一致または部分一致をチェック
        return actualStr === targetVal || actualStr.includes(targetVal);
      });
    case "notin":
      const notInTargetValues = String(target)
        .split(",")
        .map((v) => v.trim());
      const notInActualStr = String(actualValue).trim();
      return !notInTargetValues.some((targetVal) => {
        return (
          notInActualStr === targetVal || notInActualStr.includes(targetVal)
        );
      });
    case "exist":
      return (
        actualValue !== "" && actualValue !== null && actualValue !== undefined
      );
    case "notexist":
      return (
        actualValue === "" || actualValue === null || actualValue === undefined
      );
    default:
      return false;
  }
}

// デバッグ用：マスタデータの内容を確認
function debugMasterData() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const masterSheet = ss.getSheetByName(SHEET_NAMES.MASTER);
  const masterData = loadMasterData(masterSheet);

  console.log("=== マスタデータ ===");
  for (const outputItem in masterData) {
    console.log(`出力項目: ${outputItem}`);
    for (const person in masterData[outputItem]) {
      console.log(`  人物: ${person}`);
      masterData[outputItem][person].forEach((rule, index) => {
        console.log(`    ルール${index + 1}: ${JSON.stringify(rule)}`);
      });
    }
  }
}

// デバッグ用：特定物件の採点詳細を確認
function debugScoring(propertyNo = 1) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const propertySheet = ss.getSheetByName(SHEET_NAMES.PROPERTY);
  const masterSheet = ss.getSheetByName(SHEET_NAMES.MASTER);
  const wifeSheet = ss.getSheetByName(SHEET_NAMES.WIFE);

  // 物件情報のヘッダーを取得
  const propertyHeaders = propertySheet
    .getRange(1, 1, 1, propertySheet.getLastColumn())
    .getValues()[0];

  // 評価シートのヘッダーを取得
  const evaluationHeaders = getEvaluationHeaders(wifeSheet);
  const wifeWeights = getEvaluationWeights(wifeSheet, evaluationHeaders.length);

  // 対象物件を取得
  const properties = getTargetProperties(
    propertySheet,
    "selected",
    String(propertyNo)
  );
  if (properties.length === 0) {
    console.log(`物件No.${propertyNo}が見つかりません`);
    return;
  }

  const property = properties[0];
  const masterData = loadMasterData(masterSheet);

  console.log(`=== 物件No.${propertyNo}の採点詳細 ===`);
  console.log("物件情報:", property.values);
  console.log("ヘッダー:", propertyHeaders);

  // 各評価項目の詳細
  for (let j = 0; j < evaluationHeaders.length; j++) {
    const outputItem = evaluationHeaders[j];
    const weight = Number(wifeWeights[j]);

    console.log(`\n--- ${outputItem} (重み: ${weight}) ---`);

    // マスターから対応する入力項目とその値を特定
    const { inputItem, value } = findInputValueForOutputItem(
      masterData,
      outputItem,
      propertyHeaders,
      property.values,
      PERSON.WIFE
    );

    console.log(`入力項目: ${inputItem}`);
    console.log(`取得値: ${value}`);

    // マスタのルールを表示
    if (masterData[outputItem] && masterData[outputItem][PERSON.WIFE]) {
      console.log("適用可能なルール:");
      masterData[outputItem][PERSON.WIFE].forEach((rule, index) => {
        const matches = matchValue(rule.operator, rule.target, value);
        console.log(
          `  ルール${index + 1}: ${rule.operator} ${rule.target} → スコア${
            rule.score
          } (マッチ: ${matches})`
        );
      });
    }

    // スコア計算
    const score = getScoreFromMaster(
      masterData,
      outputItem,
      value,
      PERSON.WIFE
    );
    console.log(`最終スコア: ${score}`);
    console.log(`重み付けスコア: ${score * weight}`);
  }
}

// HTML UIから呼び出すためのラッパー関数
function runScoringAll() {
  try {
    const result = main("all");
    return {
      status: "success",
      message: "全物件の採点が完了しました",
      scored_properties: result.processedCount,
      target_properties: result.targetProperties,
      timestamp: new Date().toLocaleString("ja-JP"),
    };
  } catch (error) {
    console.error("採点処理でエラーが発生しました:", error);
    return {
      status: "error",
      error_message: error.message || "採点処理中にエラーが発生しました",
    };
  }
}

// HTML UIから呼び出すためのラッパー関数（指定物件）
function runScoringSelected(propertyNumbers) {
  try {
    const result = main("selected", propertyNumbers);
    return {
      status: "success",
      message: `物件番号 ${propertyNumbers} の採点が完了しました`,
      scored_properties: result.processedCount,
      target_properties: result.targetProperties,
      timestamp: new Date().toLocaleString("ja-JP"),
    };
  } catch (error) {
    console.error("採点処理でエラーが発生しました:", error);
    return {
      status: "error",
      error_message: error.message || "採点処理中にエラーが発生しました",
    };
  }
}

// UIからの実行用関数（既存）
function runScoringAllFromMenu() {
  try {
    main("all");
    SpreadsheetApp.getActiveSpreadsheet().toast(
      "全物件の採点が完了しました",
      "採点完了"
    );
  } catch (error) {
    console.error("採点処理でエラーが発生しました:", error);
    SpreadsheetApp.getActiveSpreadsheet().toast(
      `エラーが発生しました: ${error.message}`,
      "エラー"
    );
  }
}

// 特定の物件のみ採点する関数（既存）
function runScoringSelectedFromMenu() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.prompt(
    "物件採点",
    "採点する物件番号をカンマ区切りで入力してください（例: 1,2,3）:",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() === ui.Button.OK) {
    const targetNos = response.getResponseText();
    if (targetNos.trim()) {
      try {
        main("selected", targetNos);
        SpreadsheetApp.getActiveSpreadsheet().toast(
          `指定した物件(${targetNos})の採点が完了しました`,
          "採点完了"
        );
      } catch (error) {
        console.error("採点処理でエラーが発生しました:", error);
        ui.alert(`エラーが発生しました: ${error.message}`);
      }
    } else {
      ui.alert("物件番号が入力されていません");
    }
  }
}

// メニュー追加
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu("物件採点")
    .addItem("全物件採点実行", "runScoringAllFromMenu")
    .addItem("選択物件採点実行", "runScoringSelectedFromMenu")
    .addSeparator()
    .addItem("マスタデータ確認", "debugMasterData")
    .addItem("採点詳細確認(物件No.1)", "debugScoring")
    .addItem("マッチングテスト", "testMatching")
    .addToUi();
}

// デバッグ用：マッチング詳細を確認する関数
function debugMatching(outputItem, actualValue, targetValue, operator) {
  console.log(`=== マッチング詳細 ===`);
  console.log(`出力項目: ${outputItem}`);
  console.log(`実際の値: "${actualValue}" (型: ${typeof actualValue})`);
  console.log(`目標値: "${targetValue}" (型: ${typeof targetValue})`);
  console.log(`演算子: "${operator}"`);

  const result = matchValue(operator, targetValue, actualValue);
  console.log(`マッチ結果: ${result}`);

  // in演算子の場合の詳細
  if (String(operator).replace(/^'/, "") === "in") {
    const targetValues = String(targetValue)
      .split(",")
      .map((v) => v.trim());
    const actualStr = String(actualValue).trim();
    console.log(`分割された目標値: [${targetValues.join(", ")}]`);
    console.log(`実際の値(文字列): "${actualStr}"`);

    targetValues.forEach((targetVal, index) => {
      const exactMatch = actualStr === targetVal;
      const partialMatch = actualStr.includes(targetVal);
      console.log(
        `  目標値${
          index + 1
        } "${targetVal}": 完全一致=${exactMatch}, 部分一致=${partialMatch}`
      );
    });
  }

  return result;
}

// テスト用：特定の条件でマッチングをテスト
function testMatching() {
  console.log("=== マッチングテスト ===");

  // 間取りのテスト
  debugMatching("間取り", "1LDK", "2K,1LDK", "in");
  debugMatching("間取り", "2DK", "2DK", "in");

  // 建物種別のテスト
  debugMatching("建物種別", "マンション", "マンション", "'=");

  // 構造のテスト
  debugMatching("構造", "鉄筋コン", "鉄筋コン", "'=");
}
