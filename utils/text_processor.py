import re


def extract_number_from_text(text):
    """文字列から数値のみを抽出する関数"""
    if not text:
        return ""
    return re.sub(r"[^\d.]", "", text)


def process_currency(text):
    """通貨表記から数値のみを抽出する関数"""
    if not text:
        return ""
    # 万円表記の場合は10000倍する（例: 5.5万円 → 55000）
    if "万円" in text or "万" in text:
        number = re.findall(r"(\d+(?:\.\d+)?)", text)
        if number:
            try:
                return str(float(number[0]) * 10000)
            except (ValueError, IndexError):
                return ""
    # 円表記の場合はそのまま数値を抽出
    return extract_number_from_text(text)


def process_age(text):
    """築年数表記を処理する関数"""
    if not text:
        return ""
    if "新築" in text:
        return "0"
    return extract_number_from_text(text)


def process_area(text):
    """面積表記から数値を抽出する関数"""
    if not text:
        return ""
    # m²表記から数値のみを抽出
    return extract_number_from_text(text)


def clean_text(text):
    """テキストの余分な空白や改行を削除"""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()
