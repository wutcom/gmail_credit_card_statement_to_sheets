import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pypdf import PdfReader


AMOUNT_PATTERNS = [
    r"ยอดที่ต้องชำระ\s*([\d,]+\.\d{2})",
    r"Amount Due\s*([\d,]+\.\d{2})",
    r"Total Amount Due\s*([\d,]+\.\d{2})",
    r"Payment Amount\s*([\d,]+\.\d{2})",
]

DUE_DATE_PATTERNS = [
    r"วันครบกำหนดชำระ\s*(\d{2}/\d{2}/\d{4})",
    r"Payment Due Date\s*(\d{2}/\d{2}/\d{4})",
    r"Due Date\s*(\d{2}/\d{2}/\d{4})",
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


def parse_amount(text: str) -> Optional[float]:
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", "")
            return float(value)
    return None


def normalize_date(date_text: str) -> str:
    # Supports DD/MM/YYYY.
    # If the year is Buddhist Era, convert to Christian Era.
    date_value = datetime.strptime(date_text, "%d/%m/%Y")

    if date_value.year > 2400:
        date_value = date_value.replace(year=date_value.year - 543)

    return date_value.strftime("%Y-%m-%d")


def parse_due_date(text: str) -> Optional[str]:
    for pattern in DUE_DATE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalize_date(match.group(1))
    return None


def parse_statement(pdf_path: str, password: str) -> Dict:
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
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    output_path = Path(log_dir) / f"{safe_name}.txt"
    output_path.write_text(text, encoding="utf-8")
    return str(output_path)
