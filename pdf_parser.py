import re
from pypdf import PdfReader


AMOUNT_PATTERNS = [
    r"ยอดเงินที่ต้องชำระทั้งสิ้น.*?([\d,]+\.\d{2})",
    r"Total Amount Due.*?([\d,]+\.\d{2})",
    r"ยอดคงเหลือ.*?([\d,]+\.\d{2})",
    r"ยอดผ่อนชำระรายเดือน.*?([\d,]+\.\d{2})",
    r"Installment.*?([\d,]+\.\d{2})",
    r"Amount Due.*?([\d,]+\.\d{2})",
]

DUE_DATE_PATTERNS = [
    r"วันที่ครบกำหนดชำระ.*?(\d{2}/\d{2}/\d{2,4})",
    r"Due Date.*?(\d{2}/\d{2}/\d{2,4})",
    r"กำหนดชำระ.*?(\d{2}/\d{2}/\d{2,4})",
]


def extract_pdf_text(pdf_path: str, password: str) -> str:
    reader = PdfReader(pdf_path)

    if reader.is_encrypted:
        result = reader.decrypt(password)
        if result == 0:
            raise ValueError("PDF password is incorrect or PDF cannot be decrypted")

    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")

    return "\n".join(text_parts)


def normalize_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_amount(text: str):
    text = normalize_text(text)

    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))

    return None


def normalize_date(date_text: str) -> str:
    day, month, year = date_text.split("/")

    day = int(day)
    month = int(month)
    year = int(year)

    if year < 100:
        year += 2500

    if year > 2400:
        year -= 543

    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_due_date(text: str):
    text = normalize_text(text)

    for pattern in DUE_DATE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalize_date(match.group(1))

    return None


def parse_statement(pdf_path: str, password: str):
    text = extract_pdf_text(pdf_path, password)

    amount_due = parse_amount(text)
    due_date = parse_due_date(text)

    if amount_due is None or due_date is None:
        return {
            "success": False,
            "text": text,
            "amount_due": amount_due,
            "due_date": due_date,
            "error": "Cannot extract amount due or due date",
        }

    return {
        "success": True,
        "text": text,
        "amount_due": amount_due,
        "due_date": due_date,
        "error": None,
    }


def save_raw_text(log_dir: str, filename: str, text: str):
    import os

    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"{filename}.txt")

    with open(path, "w", encoding="utf-8") as file:
        file.write(text)

    return path
